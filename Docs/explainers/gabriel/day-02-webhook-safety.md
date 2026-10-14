# Day 2 — Webhook safety (and the release stub)

Owner: Gabriel · Branch: `gabriel/day-02-webhooks` · Spec: [Webhooks and idempotency](../../spec.md#payments-escrow-and-ledger)

## 1. In one paragraph

Stripe, Paystack and the escrow partner tell us about money by calling our webhooks: "the client paid", "the transfer arrived", "the hold is confirmed". Two things can go wrong. A **forged** webhook (anyone can POST to a public URL) could make us record money that never arrived. A **re-delivered** webhook (providers retry whenever they don't get a quick 200, and sometimes send the same event twice anyway) could make us count the same payment twice. Either would put our ledger out of step with the real money. Today's work closes both holes. Every webhook's signature is checked on the raw bytes before anything is read. Every verified event is stored once in `payment_events` under a unique `(provider, event_id)`, so a second delivery is recognised and does nothing. The event row, the ledger entries, the state change and the audit entry are written in one database transaction, so a failure leaves nothing half-done and the provider's retry is processed properly. The `request_release` stub Lilian needed was merged separately in #20.

## 2. How it works

```mermaid
sequenceDiagram
    autonumber
    participant P as Provider (Stripe / Paystack / escrow)
    participant R as POST /api/v1/webhooks/{provider}
    participant S as signatures.verify_*
    participant W as webhooks.process
    participant DB as Postgres
    participant H as Registered handler

    P->>R: raw body + signature header
    R->>S: check signature on the RAW bytes
    alt missing / wrong / stale signature
        S-->>R: AppError 400 invalid_signature
        R-->>P: 400 (nothing stored)
    end
    R->>W: parsed JSON
    W->>DB: SAVEPOINT; INSERT payment_events ... ON CONFLICT DO NOTHING
    alt already stored
        DB-->>W: no row
        W-->>R: DUPLICATE
        R-->>P: 200 {"duplicate": true}
    else first delivery
        W->>H: handler(session, event, request)
        H->>DB: ledger + state change + audit (same transaction)
        alt handler raises
            W->>DB: ROLLBACK TO SAVEPOINT (event row gone too)
            R-->>P: 5xx, so the provider retries
        else ok
            W->>DB: processed_at = now()
            R->>DB: COMMIT
            R-->>P: 200 {"duplicate": false}
        end
    end
```

When two deliveries of the same event race, the second `INSERT` waits on the unique index. If the first commits, the second sees a duplicate. If the first rolls back, the second inserts and processes the event itself. A test runs this race on two real connections.

Event types without a handler are still stored and acknowledged with 200, with `processed_at` left `NULL` ("received, nothing to do yet").

## 3. The three signature schemes

| | Stripe | Paystack | Escrow partner |
| --- | --- | --- | --- |
| Header | `Stripe-Signature` | `x-paystack-signature` | `X-Escrow-Signature` |
| Algorithm | Stripe's scheme: HMAC-SHA256 of `"<timestamp>.<body>"`; checked by the official `stripe` library | hex HMAC-SHA512 of the raw body | hex HMAC-SHA256 of the raw body |
| Secret | `STRIPE_WEBHOOK_SECRET` (`whsec_...`) | `PAYSTACK_SECRET_KEY` (the same key that calls the API) | `ESCROW_WEBHOOK_SECRET` |
| Replay window | 5 minutes (Stripe's default tolerance) | none from Paystack; duplicates stopped by `payment_events` | none; duplicates stopped by `payment_events` |
| Event id | `id` (`evt_...`) | none sent, so ours is `"<event>:<data.id>"` | `id` |

All comparisons are constant-time. If a secret is empty, that provider's webhook answers **503 `webhook_not_configured`**. An unset secret never means "accept anything".

## 4. Data model

**`payment_events`** (base/payments)

| Column | Type | Notes |
| --- | --- | --- |
| id | UUID | |
| provider | varchar(20) | `stripe`, `paystack` or `escrow` (check constraint) |
| event_id | varchar(255) | the provider's event id (see table above for Paystack) |
| event_type | varchar(100) | e.g. `checkout.session.completed`. Not in the spec's column list; added so handlers and ops can filter without opening the JSON |
| payload | JSONB | the full verified body |
| processed_at | timestamptz, null | set when a handler finished; `NULL` = stored, no handler ran |
| created_at, updated_at | timestamptz | UTC |

Unique `(provider, event_id)` = `uq_payment_events_provider_event_id`.

**`escrow_accounts`** (features/escrow), one per project

| Column | Type | Notes |
| --- | --- | --- |
| project_id | UUID, unique, FK → projects | |
| provider | varchar(50) | from `ESCROW_PROVIDER` (`simulated` today) |
| provider_account_ref | varchar(255), null | the partner's account id, once a partner exists |
| currency | char(3) | `NGN` |
| balance_minor | bigint ≥ 0 | **cache only**; the ledger account `escrow:{project}:NGN` is the source of truth |

Migration: `create_payment_events_escrow` (after `create_boq`).

## 5. Functions teammates can call

```python
from app.base.payments import webhooks

@webhooks.handles("stripe", "checkout.session.completed")
async def on_checkout_completed(session, event, request) -> None:
    ...  # event.payload is the verified JSON; write ledger + state + audit; never commit

from app.features.escrow import service as escrow
account = await escrow.get_or_create_account(session, project_id, "NGN", lock=True)  # idempotent

release = await escrow.request_release(session, milestone_id, actor)  # stub until day 4 (#20)
```

Lower level, used by `webhooks.process`: `payments.record_event(session, provider, event_id, event_type, payload)` returns `(EventResult.NEW, event)` or `(EventResult.DUPLICATE, None)`, and `payments.mark_processed(session, event)`.

Put handlers in a module your `router.py` imports, so they are registered when the app starts.

## 6. How to test locally

```bash
cd backend
# Tests (temporary PostGIS on 5433 if 5432 is taken):
export DATABASE_URL=postgresql+psycopg://ibackhome:ibackhome@127.0.0.1:5433/ibackhome
uv run pytest -q app/base/payments/tests/test_webhooks.py app/features/escrow/tests/test_accounts.py
```

**Stripe, for real.** Run `docker compose up` with `STRIPE_WEBHOOK_SECRET` set in `.env` to the `whsec_...` that `stripe listen` prints:

```bash
stripe listen --forward-to http://127.0.0.1:8000/api/v1/webhooks/stripe
stripe trigger checkout.session.completed      # 200; trigger again → stored again under a new evt_ id
```

To see a duplicate, use **Resend** on an event in the Stripe dashboard (Developers → Events) or `stripe events resend evt_...`. The answer is `{"received": true, "duplicate": true}`.

**Paystack, by hand** (signed with your test secret key):

```bash
BODY='{"event":"transfer.success","data":{"id":12345,"reference":"test-ref"}}'
SIG=$(printf '%s' "$BODY" | openssl dgst -sha512 -hmac "$PAYSTACK_SECRET_KEY" | sed 's/^.*= //')
curl -s -X POST http://127.0.0.1:8000/api/v1/webhooks/paystack \
  -H "Content-Type: application/json" -H "x-paystack-signature: $SIG" -d "$BODY"
# run it again → "duplicate": true; change one character of BODY without re-signing → 400
```

## 7. Decisions, deviations, limitations

- **Escrow webhook scheme is ours** (HMAC-SHA256, `X-Escrow-Signature`) until a partner is chosen (spec open decision 2). The partner's own scheme replaces `verify_escrow` and nothing else changes.
- **Paystack has no event id**, so the dedupe key is `"<event>:<data.id>"`. A transfer that succeeds and is later reversed is two events, as it should be.
- **`event_type` column** added to `payment_events` (not in the spec's column list).
- **Unknown event types are stored**, so nothing a provider sends is lost; they can be replayed once a handler exists.
- **Handlers run inside a savepoint**, so a failing handler never leaves an event row behind, even in the shared test session.
- **Limitation:** no replay tool yet for stored events whose `processed_at` is `NULL`. Reconciliation (`payments.reconcile`, spec "Background jobs") is still to come.

## 8. What's next

Day 3: real handlers. Stripe `checkout.session.completed` writes the ledger, holds in escrow and marks the milestone funded. Paystack `transfer.*` updates payout status. Funding starts with `POST /projects/{id}/funding`.
