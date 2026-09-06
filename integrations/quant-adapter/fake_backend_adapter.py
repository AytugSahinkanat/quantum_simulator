"""SS-05 Kalibrasyon ve QPU Entegrasyonu — açık kaynak (fake backend) modu.

Karar (2026-09): İlk fazda gerçek QuanT bağlantısı YOK. Bunun yerine Qiskit'in
resmi Fake Provider'ındaki, artık emekli gerçek IBM cihazlarından alınmış
anonimleştirilmiş kalibrasyon anlık görüntülerini kullanıyoruz. Bunlar gerçek
donanım ölçümü — üretilmiş sahte sayı değil; sadece cihazın kendisi artık
canlı kullanımda değil. QuanT erişimi geldiğinde bu adaptör `live` moduna
geçecek (bkz. .env QUANT_ADAPTER_MODE), API/worker sözleşmesi değişmeyecek.

Neden burada, worker'da değil: FastAPI (senkron API) tarafından da
listeleme/okuma amaçlı çağrılabilmesi için hafif tutuldu — ağır simülasyon
işi (SS-06/07) yine worker'dadır.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from qiskit_ibm_runtime.fake_provider import FakeProviderForBackendV2

_provider = FakeProviderForBackendV2()


@dataclass
class CalibrationSnapshot:
    """HLD 3.5.2 "Kalibrasyon" veri kategorisiyle aynı alanlar."""

    device_id: str
    source: str  # "open-source-fake-backend" | "live" (gelecekte)
    num_qubits: int
    captured_at: str
    avg_t1_us: Optional[float]
    avg_t2_us: Optional[float]
    avg_gate_error: Optional[float]
    avg_readout_error: Optional[float]
    coupling_map_edges: int


def list_backends() -> list[str]:
    """Kullanılabilir açık kaynak cihaz snapshot'larının adları."""
    return sorted(b.name for b in _provider.backends())


def get_snapshot(device_id: str) -> CalibrationSnapshot:
    """Tek bir fake backend'in kalibrasyon özetini HLD şemasına dönüştürür.

    Eksik alan varsa "mevcut değil" ilkesine uygun olarak None bırakılır,
    uydurulmaz (PKE-Plan K-02, A-02).
    """
    backend = _provider.backend(device_id)
    target = backend.target

    t1s, t2s, gate_errors, readout_errors = [], [], [], []
    for qubit_props in getattr(target, "qubit_properties", None) or []:
        if qubit_props is None:
            continue
        if qubit_props.t1 is not None:
            t1s.append(qubit_props.t1 * 1e6)
        if qubit_props.t2 is not None:
            t2s.append(qubit_props.t2 * 1e6)

    for op_name in target.operation_names:
        for qargs, props in (target[op_name] or {}).items():
            if props is None:
                continue
            if op_name == "measure" and props.error is not None:
                readout_errors.append(props.error)
            elif props.error is not None:
                gate_errors.append(props.error)

    def _avg(values: list[float]) -> Optional[float]:
        return sum(values) / len(values) if values else None

    return CalibrationSnapshot(
        device_id=device_id,
        source="open-source-fake-backend",
        num_qubits=backend.num_qubits,
        captured_at=datetime.now(timezone.utc).isoformat(),
        avg_t1_us=_avg(t1s),
        avg_t2_us=_avg(t2s),
        avg_gate_error=_avg(gate_errors),
        avg_readout_error=_avg(readout_errors),
        coupling_map_edges=len(target.build_coupling_map().get_edges())
        if target.build_coupling_map()
        else 0,
    )
