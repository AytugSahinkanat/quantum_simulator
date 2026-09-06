"""SS-04 Devre İşleme — senkron hızlı yol (HLD 3.7.1).

Kapsam: sözdizimi/anlam doğrulama, qubit sınırı kontrolü (FR-03: mevcut
sürümde 5 qubit), özellik çıkarımı (FR-04) ve devre hash'i (izlenebilirlik,
Analiz Raporu FR-01 kabul kriteri: aynı devre → aynı hash).

Bilinçli olarak burada YOK: transpilation sonrası fiziksel qubit eşlemesi
(coupling-map, FR-05) ve kalibrasyon bağlamı — onlar SS-05'te, ayrı router.
"""
import hashlib

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from qiskit import QuantumCircuit
from qiskit.qasm3 import loads as loads_qasm3

from app import models
from app.db import get_db
from app.schemas.circuits import (
    CircuitFeatures,
    CircuitInput,
    CircuitValidationResult,
    ValidationError_,
)

router = APIRouter(prefix="/circuits", tags=["circuits"])

# Karar (2026-09): ilk fazda gerçek QuanT'a bağlı sabit 5-qubit sınırı YOK.
# Açık kaynak / fake-backend verileriyle esnek qubit sayısında geliştiriyoruz.
# Sabit bir tavan koymak yerine, simülasyon maliyetine göre bilgilendirici bir
# risk notu döndürüyoruz — devre reddedilmez, kullanıcı bilinçli ilerler.
# Eşikler Qiskit Aer'in gürültülü (density-matrix) simülasyon maliyetine dayanır:
# her ek qubit hafıza ihtiyacını ~4 kat artırır.
SIM_RISK_LOW_MAX = 15   # ideal + gürültülü simülasyon rahat çalışır
SIM_RISK_MEDIUM_MAX = 25  # ideal rahat; gürültülü simülasyon yavaşlayabilir


def _simulation_note(num_qubits: int) -> str:
    if num_qubits <= SIM_RISK_LOW_MAX:
        return "low"
    if num_qubits <= SIM_RISK_MEDIUM_MAX:
        return "medium — gürültülü (density-matrix) simülasyon yavaşlayabilir"
    return "high — bu qubit sayısında yalnızca ideal/statevector simülasyon önerilir"


def _parse(qasm_text: str) -> QuantumCircuit:
    """PR-03: birincil format OpenQASM 3.0; QASM 2.0 istemciler için de kabul edilir.

    Sürüm başlığına (OPENQASM 3.0; / OPENQASM 2.0;) bakıp DOĞRU parser'ı seçiyoruz.
    Yanlış parser'ı deneyip gerçek hatayı bir sonraki denemenin alakasız hata
    mesajıyla gizlemek NFR-03'ü (açıklayıcı hata) ihlal eder.
    """
    header = qasm_text.strip().splitlines()[0] if qasm_text.strip() else ""
    if "3.0" in header:
        return loads_qasm3(qasm_text)
    return QuantumCircuit.from_qasm_str(qasm_text)


def _circuit_hash(qasm_text: str) -> str:
    """FR-01 kabul kriteri: aynı devre yeniden gönderildiğinde aynı hash üretilir."""
    normalized = "\n".join(line.strip() for line in qasm_text.strip().splitlines())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _extract_features(qc: QuantumCircuit) -> CircuitFeatures:
    """FR-04: qubit sayısı, derinlik, gate sayıları, ölçüm sayısı."""
    op_counts = qc.count_ops()
    two_qubit = sum(
        count
        for name, count in op_counts.items()
        if name not in {"measure", "barrier", "id"}
        and qc.data
        and any(len(instr.qubits) == 2 for instr in qc.data if instr.operation.name == name)
    )
    return CircuitFeatures(
        num_qubits=qc.num_qubits,
        num_clbits=qc.num_clbits,
        depth=qc.depth(),
        gate_count_total=sum(op_counts.values()),
        gate_count_two_qubit=two_qubit,
        measurement_count=op_counts.get("measure", 0),
    )


def _persist(
    db: Session,
    qasm_text: str,
    circuit_hash: str,
    features: CircuitFeatures,
    risk: str,
) -> str:
    """Circuit + CircuitFeature + AnalysisSession'ı kalıcılaştırır (HLD 3.5.1/3.5.3).

    circuit_hash unique olduğundan aynı devre tekrar gönderilirse yeni Circuit
    satırı açılmaz (FR-01), ama her gönderim için ayrı bir AnalizOturumu
    (analysis_session) oluşur — Analiz Raporu 4.3: "bir analiz oturumu tam
    olarak bir devreyi analiz eder", aynı devre birden çok oturumda yer alabilir.
    """
    circuit = db.query(models.Circuit).filter_by(circuit_hash=circuit_hash).first()
    if circuit is None:
        circuit = models.Circuit(
            circuit_hash=circuit_hash,
            qasm_text=qasm_text,
            num_qubits=features.num_qubits,
            num_clbits=features.num_clbits,
        )
        db.add(circuit)
        db.flush()  # circuit.id üretilsin

        db.add(
            models.CircuitFeature(
                circuit_id=circuit.id,
                depth=features.depth,
                gate_count_total=features.gate_count_total,
                gate_count_two_qubit=features.gate_count_two_qubit,
                measurement_count=features.measurement_count,
                simulation_risk=risk,
            )
        )

    session = models.AnalysisSession(circuit_id=circuit.id, status="validated")
    db.add(session)
    db.commit()
    db.refresh(session)
    return session.id


@router.post("/validate", response_model=CircuitValidationResult)
def validate_circuit(
    payload: CircuitInput, db: Session = Depends(get_db)
) -> CircuitValidationResult:
    """FR-02 + FR-03: doğrulama ve qubit sınırı kontrolü.

    NFR-03 gereği hata durumunda sistem çökmez; açıklayıcı hata listesiyle döner.
    """
    try:
        qc = _parse(payload.qasm)
    except Exception as exc:  # noqa: BLE001 — kullanıcı girdisi güvenilmez, geniş yakala
        return CircuitValidationResult(
            valid=False,
            errors=[
                ValidationError_(
                    code="PARSE_ERROR",
                    message=f"Devre ayrıştırılamadı: {exc}",
                )
            ],
        )

    if qc.num_clbits == 0:
        return CircuitValidationResult(
            valid=False,
            errors=[
                ValidationError_(
                    code="NO_MEASUREMENT",
                    message="Devrede ölçüm (measure) yok; analiz için en az bir ölçüm gerekir.",
                )
            ],
        )

    circuit_hash = _circuit_hash(payload.qasm)
    features = _extract_features(qc)
    risk = _simulation_note(qc.num_qubits)
    session_id = _persist(db, payload.qasm, circuit_hash, features, risk)

    return CircuitValidationResult(
        valid=True,
        circuit_hash=circuit_hash,
        features=features,
        simulation_risk=risk,
        analysis_session_id=session_id,
        persisted=True,
    )


@router.get("")
def list_circuits(limit: int = 20, db: Session = Depends(get_db)) -> list[dict]:
    """FR-16'nın basit bir öncüsü: kaydedilmiş devrelerin geçmişi."""
    circuits = (
        db.query(models.Circuit)
        .order_by(models.Circuit.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": c.id,
            "circuit_hash": c.circuit_hash,
            "num_qubits": c.num_qubits,
            "num_clbits": c.num_clbits,
            "created_at": c.created_at.isoformat() if c.created_at else None,
            "features": {
                "depth": c.features.depth,
                "gate_count_total": c.features.gate_count_total,
                "simulation_risk": c.features.simulation_risk,
            }
            if c.features
            else None,
        }
        for c in circuits
    ]
