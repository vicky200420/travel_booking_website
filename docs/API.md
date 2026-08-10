# API

Most of the platform is server-rendered; the JSON APIs are for map features and
operational endpoints. An OpenAPI 3 schema is generated with drf-spectacular.

## Schema / docs

| URL | Description |
|---|---|
| `/api/schema/` | OpenAPI 3 (JSON/YAML) schema |
| `/api/schema/swagger-ui/` | Interactive Swagger UI |
| `/api/schema/redoc/` | ReDoc documentation |

Authentication for the schema is session-based; unauthenticated users get
read-only access (`IsAuthenticatedOrReadOnly`).

## Map APIs (`maps`)

All map endpoints return JSON and accept `lat`, `lng`, `radius` (km) params.

- `GET /maps/api/nearby/?lat=..&lng=..&radius=..&category=..&limit=..`
  Curated nearby places around an arbitrary coordinate. Requires `lat`/`lng`.
- `GET /maps/api/hotels/<slug>/nearby/?radius=..`
  Nearby places for a specific hotel.
- `GET /maps/api/landmarks/?q=..&city=..`
  Landmark / place autocomplete for location search (`q` ≥ 2 chars).

## Dashboard APIs

- `POST /dashboard/wishlist/toggle/` — add/remove a wishlist item.
  Body: `model` (`hotel`|`flight`|`package`) + `object_id`. Requires login.

## Notifications

- `GET /notifications/unread-count/` — JSON `{"count": N}` (badge).
- `POST /notifications/<pk>/read/` — mark one read (AJAX or redirect).
- `POST /notifications/mark-all-read/` — mark all read.
- `POST /notifications/<pk>/delete/` — delete one.

## Operational

- `GET /health/` — DB-backed liveness probe. `200` healthy / `503` degraded.

## Throttling

DRF endpoints are throttled: `anon 100/hour`, `user 1000/hour`.
