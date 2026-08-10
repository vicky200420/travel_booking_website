# Security

## TLS / transport security

Set `DJANGO_USE_HTTPS=True` in production (behind TLS termination). This enables:

- `SECURE_SSL_REDIRECT` (force HTTPS)
- `SECURE_PROXY_SSL_HEADER` (trust `X-Forwarded-Proto` from the reverse proxy)
- `SESSION_COOKIE_SECURE` + `CSRF_COOKIE_SECURE` (cookies only over HTTPS)
- HSTS (`SECURE_HSTS_SECONDS`, include subdomains, preload)

## Secrets

- `DJANGO_SECRET_KEY` **must** be set when `DJANGO_DEBUG=False` — settings.py
  raises `ImproperlyConfigured` otherwise (no insecure fallback in production).
- Payment gateway keys and webhook secrets are read from environment variables
  (`.env` / Docker secrets). Never commit them.

## CSRF & sessions

- All state-changing forms use Django's built-in CSRF protection.
- Only the payment **webhook** endpoint is `csrf_exempt` — webhooks carry no
  session cookie. Both gateway webhook handlers verify the signature using the
  configured webhook secret and **reject the request when the secret is unset**,
  so an empty secret can never be exploited.
- Client-side payment verification (`PaymentVerifyView`) keeps CSRF protection.

## Authentication & authorization

- DRF default permission is `IsAuthenticatedOrReadOnly` (mutations require an
  authenticated user); Basic Authentication is disabled — session auth only.
- API throttling: anonymous `100/hour`, authenticated `1000/hour`.
- Admin analytics endpoints are gated by `AdminStaffRequiredMixin`
  (`is_staff`/superuser only); authenticated non-staff users get 403.
- Every user-facing queryset is scoped to `request.user` (ownership enforced).

## Headers & mitigations

- `X-Frame-Options: DENY`, `SECURE_REFERRER_POLICY: strict-origin-when-cross-origin`,
  Django's `SecurityMiddleware` content-type sniffing/XSS protection headers.
- Error pages never leak tracebacks in production (`DEBUG=False`).

## Dependency hygiene

- Pinned versions in `requirements.txt`; `pip-audit` / `dependabot` recommended in CI.

## Operational

- `/health/` performs a real DB round-trip and returns 503 when the database is
  unreachable, for orchestrator/load-balancer probes.
- Logging is configured via `LOGGING` (console; level from `DJANGO_LOG_LEVEL`).

## Security checklist before production

1. Generate a strong `DJANGO_SECRET_KEY` and set it via a secret store.
2. Set `DJANGO_DEBUG=False` and real `DJANGO_ALLOWED_HOSTS`.
3. Set `DJANGO_USE_HTTPS=True` behind TLS.
4. Configure real `RAZORPAY_*` / `STRIPE_*` keys and webhook secrets.
5. Use PostgreSQL and Redis cache via env vars.
6. Run `python manage.py collectstatic --noinput` and serve via WhiteNoise/Nginx.
7. Run `python manage.py check --deploy` and review its warnings.
