# TravelBooking

A production-ready Django travel booking platform — flights, hotels and curated holiday packages with booking, payments, reviews, notifications, loyalty/wishlist dashboards and admin analytics.

## Features

- **Catalogue** — searchable flights, hotels and holiday packages with filters, sorting and pagination.
- **Booking flow** — session-based checkout with price breakdown, review page and confirmation.
- **Payments** — Razorpay & Stripe order creation, client-side verification and signature-verified webhooks.
- **Reviews** — verified-booking reviews with photos, helpful votes and per-item rating summaries.
- **Dashboard** — profile, bookings, payments, wishlist, reviews, notifications, settings (tabs) and loyalty/membership.
- **Admin analytics** — staff-only executive dashboard with KPI cards, charts and CSV / XLSX / PDF report exports.
- **Notifications** — in-app notification centre, email templates, travel reminders.
- **Maps** — interactive hotel & destination maps with nearby places and route info.
- **Production hardening** — security headers, cached notification badge, SEO/sitemap, PWA, structured error pages, health check, Swagger docs, Docker + CI.

## Tech Stack

- Python 3.14, Django 6.0
- Django REST Framework + drf-spectacular (OpenAPI 3 / Swagger)
- SQLite (dev) / PostgreSQL (prod, env-driven)
- WhiteNoise for static, Bootstrap 5 + Bootstrap Icons
- Gunicorn + Nginx (production), GitHub Actions CI

## Quick Start (local development)

```bash
python -m venv .venv
.venv\Scripts\activate            # Windows
pip install -r requirements.txt

copy .env.example .env           # Windows (cp on macOS/Linux)

python manage.py migrate
python manage.py runserver
```

Visit http://127.0.0.1:8000. The admin console is at `/admin/`.

### Seed demo data (optional)

```bash
python manage.py seed_flights
python manage.py seed_hotels
python manage.py seed_packages
```

### Test & lint

```bash
python manage.py test
ruff check .
```

## Environment Variables

Copy `.env.example` → `.env` and fill in values. Key settings:

| Variable | Purpose | Default |
|---|---|---|
| `DJANGO_SECRET_KEY` | Django secret. **Required when DEBUG=False** | — |
| `DJANGO_DEBUG` | `True` enables debug mode | `False` |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated hosts | `127.0.0.1,localhost` |
| `DJANGO_USE_HTTPS` | `True` enables SSL redirect / secure cookies / HSTS | `False` |
| `DJANGO_DB_ENGINE` | `django.db.backends.postgresql` in production | sqlite3 |
| `DJANGO_DB_NAME/`USER/PASSWORD/HOST/PORT` | PostgreSQL credentials | — |
| `DJANGO_CACHE_BACKEND` | Redis cache backend in production | locmem |
| `RAZORPAY_*` / `STRIPE_*` | Payment gateway keys + webhook secrets | placeholders |

## API & Operational Endpoints

- `/api/schema/` — OpenAPI 3 schema
- `/api/schema/swagger-ui/` — Swagger UI
- `/api/schema/redoc/` — ReDoc
- `/health/` — liveness/readiness probe (DB check)
- `/robots.txt`, `/sitemap.xml` — SEO
- `/offline/` — PWA offline fallback

## Deployment

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for Docker, PostgreSQL, Nginx and production settings.

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Security](docs/SECURITY.md)
- [Deployment](docs/DEPLOYMENT.md)
- [API](docs/API.md)

## License

Proprietary / internal project.
