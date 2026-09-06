"""SS-02 API & Oturum Yönetimi — giriş noktası.

Bu modül, HLD 3.3 (SS-02) sözleşmesindeki senkron hızlı yolu barındırır:
devre doğrulama, özellik çıkarımı ve yayımlanmış model tahmini.
Uzun işler (QPU run, eğitim, büyük rapor) buradan job kuyruğuna devredilir,
gerçek çalışma services/worker içinde yapılır.
"""
from fastapi import FastAPI

from app.db import Base, engine
from app.routers import calibration, circuits

app = FastAPI(
    title="QuanT Dijital İkiz API",
    version="0.1.0",
    description="Devre girişi, doğrulama, kalibrasyon bağlamı ve tahmin orkestrasyonu.",
)


@app.get("/health", tags=["ops"])
def health() -> dict:
    """Süreç ayakta mı — bağımlılık kontrolü yapmadan hızlı cevap (HLD 3.7.5)."""
    return {"status": "ok"}


@app.get("/readiness", tags=["ops"])
def readiness() -> dict:
    """DB, model registry ve zorunlu depolar kullanılabilir mi (HLD 3.7.5).

    TODO: Postgres / Redis / nesne deposu / aktif model kontrolü eklenecek (SS-10, SS-11).
    """
    return {"status": "not_implemented"}


@app.on_event("startup")
def on_startup() -> None:
    """MVP şema kurulumu — bkz. app/db.py başlığındaki Alembic notu."""
    Base.metadata.create_all(bind=engine)


app.include_router(circuits.router)  # SS-04 — devre girişi & doğrulama (FR-01..FR-04)
app.include_router(calibration.router)  # SS-05 — açık kaynak kalibrasyon (fake backend)
# TODO(SS-06/07): app.include_router(predictions.router) — simülasyon & ML tahmini
# TODO(SS-09): app.include_router(reports.router)        — metrik & rapor
