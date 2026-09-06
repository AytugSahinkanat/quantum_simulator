"""SS-05 Kalibrasyon — açık kaynak fake-backend modu (2026-09 kararı).

Gerçek QuanT bağlanana kadar bu uçlar integrations/quant-adapter/
fake_backend_adapter.py üzerinden Qiskit'in gerçek (emekli) IBM cihaz
kalibrasyonlarını döner. `source` alanı her zaman "open-source-fake-backend"
olarak işaretlenir — HLD 3.8.4 "güvenli bozunma": gerçek donanım verisiymiş
gibi gösterilmez.
"""
import sys
from pathlib import Path

from fastapi import APIRouter, HTTPException

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "integrations" / "quant-adapter"))
from fake_backend_adapter import get_snapshot, list_backends  # noqa: E402

router = APIRouter(prefix="/calibration", tags=["calibration"])


@router.get("/backends")
def get_backends() -> dict:
    """Kullanılabilir açık kaynak kalibrasyon snapshot'larının listesi."""
    return {"source": "open-source-fake-backend", "backends": list_backends()}


@router.get("/snapshot/{device_id}")
def get_backend_snapshot(device_id: str) -> dict:
    try:
        snap = get_snapshot(device_id)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=404, detail=f"Bilinmeyen cihaz: {device_id} ({exc})")
    return snap.__dict__
