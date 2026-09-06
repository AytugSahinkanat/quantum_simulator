"""FR-01..FR-04 için istek/yanıt sözleşmeleri (Analiz Raporu 3.2, 4.3 KuantumDevresi/DevreÖzellikleri)."""
from typing import Optional

from pydantic import BaseModel, Field


class CircuitInput(BaseModel):
    """FR-01: Devre girişi. OpenQASM 3.0 metni birincil format (PR-03)."""

    qasm: str = Field(..., description="OpenQASM 3.0 (veya 2.0) devre metni.")


class ValidationError_(BaseModel):
    """NFR-03: sistem çökmeden, satır/alan açıklamalı hata döner."""

    code: str
    message: str
    line: Optional[int] = None


class CircuitFeatures(BaseModel):
    """FR-04: devre özellik çıkarımı."""

    num_qubits: int
    num_clbits: int
    depth: int
    gate_count_total: int
    gate_count_two_qubit: int
    measurement_count: int


class CircuitValidationResult(BaseModel):
    """UC-01 başarılı sonucu: devre hash'i, doğrulama durumu (Analiz Raporu 4.2).

    simulation_risk: sabit qubit tavanı yok (2026-09 kararı) — bunun yerine
    devre reddedilmeden bilgilendirici bir simülasyon maliyeti notu döner.
    """

    valid: bool
    circuit_hash: Optional[str] = None
    features: Optional[CircuitFeatures] = None
    simulation_risk: Optional[str] = None
    analysis_session_id: Optional[str] = None
    persisted: bool = False
    errors: list[ValidationError_] = []
