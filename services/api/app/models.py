"""HLD 3.5.3 kavramsal şema — Analiz Raporu 4.3'teki alan modelinin
(KuantumDevresi, DevreÖzellikleri, KalibrasyonAnlıkGörüntüsü, AnalizOturumu)
ilk PostgreSQL karşılığı. Yalnızca bugüne kadar yazdığımız kadarını kapsar;
SimülasyonÇalıştırması / GürültüTahmini / ModelSürümü sonraki fazda eklenecek.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now():
    return datetime.now(timezone.utc)


class Circuit(Base):
    """KuantumDevresi. circuit_hash: FR-01 kabul kriteri — aynı devre → aynı hash."""

    __tablename__ = "circuits"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    circuit_hash = Column(String, unique=True, nullable=False, index=True)
    qasm_text = Column(String, nullable=False)
    num_qubits = Column(Integer, nullable=False)
    num_clbits = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_now)

    features = relationship("CircuitFeature", back_populates="circuit", uselist=False)


class CircuitFeature(Base):
    """DevreÖzellikleri (FR-04)."""

    __tablename__ = "circuit_features"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    circuit_id = Column(
        UUID(as_uuid=False), ForeignKey("circuits.id"), nullable=False, unique=True
    )
    depth = Column(Integer, nullable=False)
    gate_count_total = Column(Integer, nullable=False)
    gate_count_two_qubit = Column(Integer, nullable=False)
    measurement_count = Column(Integer, nullable=False)
    simulation_risk = Column(String, nullable=False)

    circuit = relationship("Circuit", back_populates="features")


class CalibrationSnapshot(Base):
    """KalibrasyonAnlıkGörüntüsü — açık kaynak fake-backend modu (2026-09 kararı).

    Append-only (HLD 3.5.4): mevcut satır güncellenmez, güncellik eşiği
    aşıldığında yeni satır eklenir (bkz. calibration.py get_or_create).
    """

    __tablename__ = "calibration_snapshots"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    device_id = Column(String, nullable=False, index=True)
    source = Column(String, nullable=False)
    num_qubits = Column(Integer, nullable=False)
    captured_at = Column(DateTime(timezone=True), nullable=False)
    avg_t1_us = Column(Float, nullable=True)
    avg_t2_us = Column(Float, nullable=True)
    avg_gate_error = Column(Float, nullable=True)
    avg_readout_error = Column(Float, nullable=True)
    coupling_map_edges = Column(Integer, nullable=False)


class AnalysisSession(Base):
    """AnalizOturumu — devre + snapshot + (ileride model) bağlamının merkezi.

    Analiz Raporu 4.3: "bir analiz oturumu tam olarak bir devreyi analiz eder".
    """

    __tablename__ = "analysis_sessions"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    circuit_id = Column(UUID(as_uuid=False), ForeignKey("circuits.id"), nullable=False)
    calibration_snapshot_id = Column(
        UUID(as_uuid=False), ForeignKey("calibration_snapshots.id"), nullable=True
    )
    status = Column(String, nullable=False, default="validated")
    created_at = Column(DateTime(timezone=True), default=_now)

    circuit = relationship("Circuit")
    calibration_snapshot = relationship("CalibrationSnapshot")
