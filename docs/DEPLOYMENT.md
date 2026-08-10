# Deployment

## Options

### 1. Docker Compose (recommended for production-ish setup)

Stack: `web` (Gunicorn) + `db` (PostgreSQL 16) + `redis` + `nginx`.

```bash
cp .env.example .env
# Edit .env: DJANGO_SECRET_KEY, DJANGO_DEBUG=False, ALLOWED_HOSTS,
# DJANGO_USE_HTTPS=True (behind TLS), payment keys, POSTGRES_PASSWORD.
docker compose up -d --build
```

- Migrations and `collectstatic` run automatically on container start
  (`deploy/entrypoint.sh`).
- Media uploads live in the named `media` volume; `/app/media` is shared
  between `web` and `nginx`.
- Nginx listens on `:80`. Put a TLS terminator (e.g. certbot / Caddy) in front
  and set `DJANGO_USE_HTTPS=True`.

### 2. Bare metal / VPS

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # configure for production
python manage.py migrate --noinput
python manage.py collectstatic --noinput
gunicorn travel_booking.wsgi:application --bind 0.0.0.0:8000 --workers 3
```

Point Nginx at Gunicorn (see `deploy/nginx.conf`) and add a TLS cert.

## Production environment checklist

| Setting | Value |
|---|---|
| `DJANGO_DEBUG` | `False` |
| `DJANGO_SECRET_KEY` | Strong random value, secret store |
| `DJANGO_ALLOWED_HOSTS` | Your real domain(s) |
| `DJANGO_USE_HTTPS` | `True` behind TLS |
| `DJANGO_DB_ENGINE` | `django.db.backends.postgresql` |
| `DJANGO_CACHE_BACKEND` | `django.core.cache.backends.redis.RedisCache` |
| `DJANGO_CACHE_LOCATION` | `redis://redis:6379/1` |
| `RAZORPAY_*` / `STRIPE_*` | Real keys + webhook secrets |
| `EMAIL_BACKEND` | `django.core.mail.backends.smtp.EmailBackend` |

Run `python manage.py check --deploy` and resolve the warnings.

## Health checks

- `GET /health/` → `200 {"status": "ok", "database": "ok"}` when the DB is
  reachable, else `503`. Wire this into your orchestrator / load balancer.

## Media in production

The app uses `MEDIA_ROOT` (local disk). In Docker this is a named volume.
For multi-server deployments, move media to object storage (e.g. S3 /
Cloudinary) — `django-storages` can be added and `DEFAULT_FILE_STORAGE` pointed
at it without code changes.

## Scaling notes

- All static assets are served compressed by WhiteNoise; Nginx proxies them.
- The only cross-process cache use is the notification badge; switch to Redis
  as above for multi-worker correctness.
- Payments are synchronous to the gateway APIs; keep Gunicorn `--timeout`
  generous (120s default in this repo).
