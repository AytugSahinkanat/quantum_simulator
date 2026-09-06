"""Worker — SS-04 (devre işleme), SS-06 (ideal/baseline sim), SS-07 (ML tahmin).

Redis kuyruğundan job devralır (lease), uzun/asenkron işleri yürütür:
ideal simülasyon, Qiskit Aer baseline, ML inference, QuanT run gönderimi,
model eğitimi ve büyük rapor üretimi (HLD 3.7.1 asenkron sınıfı).
"""


def run_worker_loop() -> None:
    """TODO: Redis job kuyruğunu dinle, lease al, heartbeat üret (HLD 3.7.2)."""
    raise NotImplementedError


if __name__ == "__main__":
    run_worker_loop()
