# Architecture

## Overview

```
Browser ──▶ Nginx ──▶ Gunicorn (Django WSGI) ──▶ PostgreSQL
              │                                    │
              └── static (WhiteNoise/manifest)     └── Redis (cache)
```

Classic server-rendered Django application. Server-rendered templates for SEO,
small JSON endpoints for map/nearby place data, and an admin analytics layer.

## Application layout

| Package | Responsibility |
|---|---|
| `accounts` | Custom user, registration, login/logout, profile, email verification |
| `flights` | Flight search + detail, seed command |
| `hotels` | Hotel list/search + detail, galleries, sitemap entry point |
| `packages` | Holiday package list/search + detail, seed command |
| `bookings` | Booking create → review → confirm flow, history, cancellation |
| `payments` | Gateway abstraction (Razorpay/Stripe), verify + webhook, invoice |
| `reviews` | Verified-booking reviews, helpful votes, rating summaries |
| `dashboard` | User hub (bookings/payments/wishlist/settings) + admin analytics |
| `maps` | Interactive map views + nearby-place JSON APIs |
| `notifications` | In-app notifications, emails, travel reminders, badge cache |
| `home` | Landing page, project-level infrastructure tests |
| `travel_booking` | Settings, root URLconf, sitemaps, health check, error handlers |

## Booking flow

1. `BookingCreateView` validates product + traveller data, computes a price
   breakdown and stashes it in the session (`booking_data`).
2. `BookingReviewView` reads the session, shows the summary and creates the
   `Booking` row via `BookingService.create_booking`.
3. `PaymentCheckoutView` initiates a gateway order; the JS verifies the payment
   client-side, then `PaymentVerifyView` confirms the signature and confirms
   the booking. Webhooks (`payment_captured` / `payment_intent.succeeded`) are
   the authoritative source and mark pending bookings paid/confirmed.

## Data model (core)

- `accounts.CustomUser` (roles: customer/agent/staff, `is_email_verified`)
- `flights.Flight`, `hotels.Hotel`, `packages.TravelPackage`
- `bookings.Booking` (generic pointer via `flight`/`hotel`/`package` + `booking_type`)
- `payments.Payment` (gateway, order_id, status)
- `reviews.Review` + `ReviewImage` + `HelpfulVote`
- `notifications.Notification`
- `dashboard.UserProfile` (travel/notification prefs), `dashboard.WishlistItem`

## Key design decisions

- **Denormalised ratings** — `average_rating`/`total_reviews` on Hotel/Package are
  kept in sync by `reviews/signals.py` so list pages never aggregate.
- **Cached notification badge** — the navbar bell reads a per-user cached summary
  (`notifications.services.NotificationService.summary`) that is invalidated on
  every mutation, avoiding two queries per page render.
- **One helpful-vote query** — review cards use a pre-computed set of the current
  user's helpful review IDs instead of an N+1 membership check.
- **Services layer** — booking/payment/dashboard business logic lives in
  `services.py` modules so views stay thin and logic is testable.
- **Generic error handlers** — custom 400/403/404/500 handlers render branded
  templates via `travel_booking.views`.

## Testing

Tests live in per-app `tests.py` (Django `TestCase`). `home/tests.py` holds
infrastructure/security/SEO tests (health, sitemap, robots, error handlers,
webhook guard, notification cache, helpful-vote scoping).
