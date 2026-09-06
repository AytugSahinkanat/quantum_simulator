"""SS-05 Kalibrasyon — açık kaynak fake-backend modu (2026-09 kararı).

Gerçek QuanT bağlanana kadar bu uçlar integrations/quant-adapter/
fake_backend_adapter.py üzerinden Qiskit'in gerçek (emekli) IBM cihaz
kalibrasyonlarını döner. `source` alanı her zaman "open-source-fake-backend"
olarak işaretlenir — HLD 3.8.4 "güvenli bozunma": gerçek donanım verisiymiş
gibi gösterilmez.

Kalıcılık: HLD 3.5.4 "Snapshot append-only" — CALIBRATION_FRESHNESS_HOURS
içinde zaten bir snapshot varsa yenisi yazılmaz, mevcut olan döner.
"""
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models
from app.db import get_db

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "integrations" / "quant-adapter"))
from fake_backend_adapter import get_snapshot, list_backends  # noqa: E402

router = APIRouter(prefix="/calibration", tags=["calibration"])

FRESHNESS_HOURS = float(os.environ.get("CALIBRATION_FRESHNESS_HOURS", "24"))


@router.get("/backends")
def get_backends() -> dict:
    """Kullanılabilir açık kaynak kalibrasyon snapshot'larının listesi."""
    return {"source": "open-source-fake-backend", "backends": list_backends()}


@router.get("/snapshot/{device_id}")
def get_backend_snapshot(device_id: str, db: Session = Depends(get_db)) -> dict:
    existing = (
        db.query(models.CalibrationSnapshot)
        .filter_by(device_id=device_id)
        .order_by(models.CalibrationSnapshot.captured_at.desc())
        .first()
    )
    if existing is not None:
        age = datetime.now(timezone.utc) - existing.captured_at
        if age < timedelta(hours=FRESHNESS_HOURS):
            return {**_row_to_dict(existing), "reused": True, "age_hours": round(age.total_seconds() / 3600, 2)}

    try:
        snap = get_snapshot(device_id)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=404, detail=f"Bilinmeyen cihaz: {device_id} ({exc})")

    row = models.CalibrationSnapshot(
        device_id=snap.device_id,
        source=snap.source,
        num_qubits=snap.num_qubits,
        captured_at=datetime.fromisoformat(snap.captured_at),
        avg_t1_us=snap.avg_t1_us,
        avg_t2_us=snap.avg_t2_us,
        avg_gate_error=snap.avg_gate_error,
        avg_readout_error=snap.avg_readout_error,
        coupling_map_edges=snap.coupling_map_edges,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {**_row_to_dict(row), "reused": False, "age_hours": 0.0}


def _row_to_dict(row: "models.CalibrationSnapshot") -> dict:
    return {
        "id": row.id,
        "device_id": row.device_id,
        "source": row.source,
        "num_qubits": row.num_qubits,
        "captured_at": row.captured_at.isoformat(),
        "avg_t1_us": row.avg_t1_us,
        "avg_t2_us": row.avg_t2_us,
        "avg_gate_error": row.avg_gate_error,
        "avg_readout_error": row.avg_readout_error,
        "coupling_map_edges": row.coupling_map_edges,
    }
