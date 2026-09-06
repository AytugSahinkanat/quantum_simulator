"""Kalıcı veri katmanı — HLD 3.5.1: PostgreSQL, tek doğru veri kaynağı.

Basitlik notu (MVP): şema Base.metadata.create_all() ile oluşturuluyor.
HLD 3.8.1 "Cold Start" gerçek sürümde kontrollü migration (Alembic) ister —
bu, ilk çalışan iskelet için bilinçli bir kısayol; okul projesinin bu
aşamasında yeterli, üretim/demo profiline geçerken Alembic'e taşınmalı.
"""
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://quant:quant@postgres:5432/quant"
)
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
