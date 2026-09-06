# QuanT Dijital İkiz Platformu

TOBB ETÜ QuanT 5-qubit kuantum bilgisayarı için kalibrasyon tabanlı gürültü tahmini ve
dijital ikiz platformu. Mimari kararlar için bkz. `docs/`.

## Dizin yapısı

| Dizin | Sorumluluk (HLD alt sistemi) | Sorumlu ikili |
|---|---|---|
| `apps/web` | Web arayüzü — SS-01 | Ali Kağan · Ahmet Yusuf |
| `services/api` | API & oturum & güvenlik — SS-02, SS-03, SS-10, SS-11 | Ali Kağan · Ahmet Yusuf |
| `services/worker` | Devre işleme, simülasyon, ML tahmini — SS-04, SS-06, SS-07 | Furkan · Ali Kağan / Ahmet Yusuf · Yunus Emre / Yunus Emre · Aytuğ |
| `integrations/quant-adapter` | QuanT protokol eşleme — SS-05 | Aytuğ · Furkan |
| `data/benchmark-circuits` | ≥50 devrelik sürümlü havuz | Furkan · Ali Kağan |
| `data/calibration-snapshots` | Kalibrasyon anlık görüntüleri | Aytuğ · Furkan |
| `infra` | Docker Compose, Nginx, ortam profilleri | tüm ekip |

## Hızlı başlangıç (Profil 1 — Geliştirme)

```bash
cp .env.example .env
docker compose -f infra/docker-compose.dev.yml up --build
```

- Web: http://localhost:5173
- API: http://localhost:8000/docs
- QPU adaptörü bu profilde `mock` modundadır (gerçek QuanT'a bağlanmaz).

## Ortam profilleri

1. **Geliştirme** — tek makine, Docker Compose, mock QPU.
2. **Entegrasyon/Test** — ortak lab sunucusu, gerçek Postgres/Redis/MinIO, sınırlı QuanT test hesabı.
3. **Demo/Üretim Prototipi** — kontrollü sunucu, TLS/RBAC/secret aktif, gerçek QuanT erişimi.

Ayrıntılı platform planı ve bağlantı diyagramı için proje sayfasına bakın (bkz. paylaşılan link).
