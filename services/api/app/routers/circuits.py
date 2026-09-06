"""SS-04 Devre İşleme — senkron hızlı yol (HLD 3.7.1).

Kapsam: sözdizimi/anlam doğrulama, qubit sınırı kontrolü (FR-03: mevcut
sürümde 5 qubit), özellik çıkarımı (FR-04) ve devre hash'i (izlenebilirlik,
Analiz Raporu FR-01 kabul kriteri: aynı devre → aynı hash).

Bilinçli olarak burada YOK: transpilation sonrası fiziksel qubit eşlemesi
(coupling-map, FR-05) ve kalibrasyon bağlamı — onlar SS-05'te, ayrı router.
"""
import hashlib

from fastapi import APIRouter
from qiskit import QuantumCircuit
from qiskit.qasm3 import loads as loads_qasm3

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


@router.post("/validate", response_model=CircuitValidationResult)
def validate_circuit(payload: CircuitInput) -> CircuitValidationResult:
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

    return CircuitValidationResult(
        valid=True,
        circuit_hash=_circuit_hash(payload.qasm),
        features=_extract_features(qc),
        simulation_risk=_simulation_note(qc.num_qubits),
    )
