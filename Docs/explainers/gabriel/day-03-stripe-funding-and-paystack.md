# Day 3 — Stripe funding and Paystack payouts

Owner: Gabriel · Branch: `gabriel/day-03-funding` (stacked on `gabriel/day-02-webhooks`) · Spec: [Payments, escrow and ledger](../../spec.md#payments-escrow-and-ledger), [Milestones state machine](../../spec.md#state-machines)

## 1. In one paragraph

Adaeze lives in Manchester and is building a duplex in Enugu. When the foundation milestone (₦1,500,000) is due, she taps **Fund**. Our API works out the pound amount at today's rate, adds our fee, and gives her a Stripe Checkout link. She pays by card on Stripe's own page. We never see her card, and her pounds land in Stripe, not in an iBackHome bank account. Nothing counts as paid yet. Only when Stripe's **signed** `checkout.session.completed` webhook reaches us do we act, all in one database transaction: we record the payment in the double-entry ledger, ask the licensed escrow partner to **hold** the naira for her project, and move the milestone from `pending` to `funded`. The money then sits with the partner until the work is verified and approved. iBackHome only keeps a ledger of where every kobo is; it never holds the funds. The same day's work also gets Paystack ready to pay contractors and suppliers in naira: bank accounts registered as Paystack recipients (stored masked) and transfers that can never be sent twice.

## 2. How it works

```mermaid
sequenceDiagram
    autonumber
    actor C as Client (Manchester)
    participant API as iBackHome API
    participant FX as FxRateSource + fees
    participant S as Stripe Checkout
    participant W as POST /webhooks/stripe
    participant DB as Postgres (one transaction)
    participant E as Escrow partner (SimulatedEscrow)

    C->>API: POST /projects/{id}/funding {milestone_id, currency: GBP} + Idempotency-Key
    API->>API: client of this project? project active? milestone pending & in project?
    API->>FX: ₦ amount → £ (round up) + fee (bps, round up)
    API->>S: create Checkout session (Idempotency-Key passed on; metadata: fx_rate, amounts…)
    S-->>API: session id + URL
    API->>DB: audit funding.checkout_created (NO ledger entries)
    API-->>C: 201 {checkout_url, total_minor, fx_rate…}
    C->>S: pays with card on Stripe's page
    S->>W: checkout.session.completed (signed)
    W->>W: verify signature on raw body
    W->>DB: INSERT payment_events (duplicate? → 200, stop)
    W->>DB: lock milestone; still pending? amounts match?
    W->>E: hold(project, ₦1,500,000, ref="stripe_checkout:cs_…")
    E-->>W: held (same ref again → same result, never a 2nd hold)
    W->>DB: ledger T1 (+fee), T2, T3 (fx_rate stored)
    W->>DB: escrow_accounts.balance_minor += ₦
    W->>DB: milestones.mark_funded() → pending→funded (+ audit milestone.funded)
    W->>DB: audit escrow.funded
    W->>DB: COMMIT (all of the above, or none)
    W-->>S: 200
```

If the escrow hold fails, the exception rolls everything back, including the `payment_events` row, and Stripe gets a 5xx. Stripe retries, the retry calls `hold` with the same `ref`, and the partner never holds twice.

## 3. Worked example with real numbers

Milestone 1 "Foundation" of project `P` = **₦1,500,000.00** = `150_000_000` kobo. Test rate **₦2,000 per £1** (`FX_NGN_PER_GBP=2000`). Fee **250 bps** (2.5%).

| Step | Calculation | Result |
| --- | --- | --- |
| Convert | ceil(150,000,000 ÷ 2000) | **75,000 p** = £750.00 |
| Fee | ceil(75,000 × 250 ÷ 10,000) | **1,875 p** = £18.75 |
| Client pays | 75,000 + 1,875 | **76,875 p** = £768.75 |

Ledger rows written by the webhook (all share `ref_type="payment_event"`, `ref_id` = the `payment_events` row):

| Transaction | Account | Debit | Credit | fx_rate |
| --- | --- | --- | --- | --- |
| T1 · GBP (payment received) | `stripe_clearing:GBP` | 76,875 | | |
| T1 · GBP | `client_funding:P:GBP` | | 75,000 | |
| T1 · GBP (our fee, its own entry) | `fees:GBP` | | 1,875 | |
| T2 · GBP (converted out) | `client_funding:P:GBP` | 75,000 | | 2000 |
| T2 · GBP | `fx_conversion:GBP` | | 75,000 | 2000 |
| T3 · NGN (held in escrow) | `escrow:P:NGN` | 150,000,000 | | 2000 |
| T3 · NGN | `fx_conversion:NGN` | | 150,000,000 | 2000 |

Each transaction balances in one currency (T1: 76,875 = 75,000 + 1,875). Balances afterwards (debits − credits, the ledger's sign convention):

| Account | Balance | Meaning |
| --- | --- | --- |
| `stripe_clearing:GBP` | +76,875 | Stripe holds £768.75 for us until it settles to the partner |
| `client_funding:P:GBP` | 0 | everything the client paid has been converted |
| `fees:GBP` | −1,875 | £18.75 fee earned |
| `fx_conversion:GBP` / `:NGN` | −75,000 / −150,000,000 | the two legs of the conversion, linked by ref |
| `escrow:P:NGN` | **+150,000,000** | the partner holds exactly ₦1,500,000.00 |

`escrow_accounts.balance_minor` for `P` = 150,000,000 (a cache that must equal the ledger). The milestone is `funded`. Audit entries: `funding.checkout_created` (actor: the client), `milestone.funded` and `escrow.funded` (actor: system).

With a less round rate, e.g. ₦2,050.50 per £1: 150,000,000 ÷ 2050.5 = 73,152.89 p, rounded **up** to 73,153 p. 73,153 × 2050.5 = ₦1,500,002.27 ≥ ₦1,500,000, so the escrow is never short and the client pays at most 1p extra.

## 4. FX and fee rules

- **Rates** are naira per one unit of the client's currency, `Decimal`, never float. They come from an `FxRateSource`. Today that is `StaticFxRates`, which reads `FX_NGN_PER_GBP`, `FX_NGN_PER_USD` and `FX_NGN_PER_EUR` and returns `FxQuote(rate, as_of (UTC), source="static")`. A live provider can replace it with no other change.
- **Conversion rounding** (applied once, in `foreign_minor_for_ngn`): the client-currency amount is **rounded up** to a whole penny or cent. The naira side is fixed because it is what the escrow must hold. Minor-unit exponents (NGN, GBP, USD, EUR = 2) are part of the formula.
- **Fee**: `ceil(net_minor × FUNDING_FEE_BPS ÷ 10,000)`, integer arithmetic only, charged on top of the converted amount. It shows as its own line on the Checkout page.
- **Where the rate is stored**: in the Stripe session metadata (`fx_rate`, `fx_as_of`, `fee_bps`, amounts), so the webhook uses the rate the client was quoted, not today's. It is also stored on the `fx_rate` column of the T2 and T3 ledger entries, and in the `escrow.funded` audit entry.
- **Supported currencies**: GBP, USD, EUR. Anything else is refused with 422.

## 5. Paystack setup

- **Client** (`base/payments/paystack.py`): an httpx client behind a `PaystackClient` Protocol, authenticated with `PAYSTACK_SECRET_KEY` (an `sk_test_...` key in test mode). Errors map to 422 `paystack_refused` (Paystack's message, e.g. "Account number is invalid"), 502 `paystack_unavailable` (network or 5xx), and 503 `paystack_not_configured`.
- **Recipients**: `register_payout_recipient(...)` calls `POST /transferrecipient` (`type: nuban`, NGN) for a contractor (`user_id`) or a supplier (`supplier_id`).
  - **We store** recipient_code, bank code and name, account name, and the **masked** number `******6789`.
  - **We never store the full account number.** A database check constraint refuses any value that isn't masked, and the full number is never logged or written to the audit log.
  - Registering the same account for the same owner returns the existing row. Registering an account that belongs to someone else returns 409.
- **Transfers**: `initiate_transfer(session, recipient_code, amount_minor, reference, reason=...)` calls `POST /transfer` with **our** `reference` (16–50 characters: lower-case letters, digits, `-`, `_`).
  - The same reference with the same details returns the existing payout with no second API call. The same reference with different details returns 409.
  - Paystack also refuses a reference it has already seen.
- **Webhooks**: `transfer.success`, `transfer.failed` and `transfer.reversed` are handled in `base/payments/handlers.py`. They move the payout `pending → success | failed | reversed` (or `success → reversed`) and write an audit entry `payout.<status>`.
  - A status the payout already has changes nothing.
  - An unknown reference, or a move that isn't allowed (e.g. `failed → success`), is logged and acknowledged with 200, so Paystack doesn't retry it forever.
- **Paystack dashboard**: turn off "OTP for transfers" for API transfers, and set the webhook URL to `/api/v1/webhooks/paystack`. Paystack signs webhooks with the same secret key.
- **Not yet**: ledger entries for payouts (debit `escrow_payouts`, credit `contractor_payable`). Those come with releases on Day 4.

## 6. Data model and endpoints

**New tables** (migration `create_payouts`, after `create_payment_events_escrow`):

| `payout_recipients` | | `payouts` | |
| --- | --- | --- | --- |
| user_id → users (or) | supplier_id (no FK until suppliers has a table) | recipient_id → payout_recipients | reference (unique, ours) |
| provider (`paystack`) | recipient_code (unique) | amount_minor (> 0), currency `NGN` | reason |
| bank_code, bank_name | account_name | status (`pending`, `success`, `failed`, `reversed`) | provider_transfer_code |
| account_number_masked (`******1234`, checked) | currency | failure_reason | completed_at |

Exactly one of `user_id` / `supplier_id` is set (check constraint). Both tables also have `id`, `created_at` and `updated_at`.

**`POST /api/v1/projects/{project_id}/funding`**: client only, and only the project's own client.

```http
POST /api/v1/projects/7a96c16a-0d3a-441e-93e3-2fa4c983ae5e/funding
Authorization: Bearer <client access token>
Idempotency-Key: 5d0c1e9e-fund-foundation
Content-Type: application/json

{"milestone_id": "0b6f4c1e-3f3a-4d47-9a55-6f7d2c1e8a10", "currency": "GBP"}
```

```json
201 Created
{
  "project_id": "7a96c16a-0d3a-441e-93e3-2fa4c983ae5e",
  "milestone_id": "0b6f4c1e-3f3a-4d47-9a55-6f7d2c1e8a10",
  "checkout_session_id": "cs_test_a1B2c3",
  "checkout_url": "https://checkout.stripe.com/c/pay/cs_test_a1B2c3",
  "currency": "GBP",
  "amount_ngn_minor": 150000000,
  "net_minor": 75000,
  "fee_minor": 1875,
  "fee_bps": 250,
  "total_minor": 76875,
  "fx_rate": "2000",
  "fx_as_of": "2026-10-14T09:00:00Z"
}
```

| Status | Code | When |
| --- | --- | --- |
| 401 | `unauthorized` | no or bad token |
| 403 | `forbidden_role` | not a client (contractor, ops…) |
| 403 | `not_project_member` / `not_project_client` | a client, but not this project's |
| 404 | `project_not_found` / `milestone_not_found` | |
| 409 | `project_not_active` | project is draft, boq_review, paused or completed |
| 409 | `milestone_not_in_project` | milestone belongs to another project |
| 409 | `milestone_not_pending` | already funded (or further along) |
| 422 | `validation_error` | currency not GBP, USD or EUR |
| 502 / 503 | `stripe_unavailable` / `stripe_not_configured` | |

`fx_rate` is a string, so no float ever carries money. Sending the same `Idempotency-Key` again returns the same body and calls Stripe only once; the key also goes to Stripe as `funding:{milestone_id}:{key}`.

**`POST /api/v1/webhooks/stripe`** now handles `checkout.session.completed` and `checkout.session.async_payment_succeeded`. **`POST /api/v1/webhooks/paystack`** now handles `transfer.success`, `transfer.failed` and `transfer.reversed`. Both answer `{"received": true, "duplicate": false}`.

**Service functions** (no endpoint yet, see section 8):

```python
from app.base import payments
recipient = await payments.register_payout_recipient(
    session, account_name="Chidi Okeke", account_number="0123456789", bank_code="058",
    actor_id=user.id, user_id=user.id)
payout = await payments.initiate_transfer(
    session, recipient.recipient_code, 50_000_000, f"release-{release_id.hex}", reason="Milestone 1")
```

## 7. How to run and test it locally

**Automated tests** (no network; Stripe faked, Paystack mocked with respx):

```bash
cd backend
uv sync
export DATABASE_URL=postgresql+psycopg://ibackhome:ibackhome@127.0.0.1:5433/ibackhome   # or your compose db
uv run pytest -q app/base/payments app/features/escrow
uv run ruff check . && uv run ruff format --check . && uv run mypy app
```

**Manual end-to-end with a real Stripe test payment.**

1. In the repo-root `.env`, set:
   ```
   STRIPE_SECRET_KEY=sk_test_...
   STRIPE_WEBHOOK_SECRET=whsec_...      # printed by `stripe listen` in step 2
   PAYSTACK_SECRET_KEY=sk_test_...
   ```
   Then run `docker compose up -d --build` and `docker compose exec api python scripts/seed.py`.
2. In a second terminal, run `stripe listen --forward-to http://127.0.0.1:8000/api/v1/webhooks/stripe`. Copy the `whsec_...` it prints into `.env`, then `docker compose restart api`.
3. Get to an active project with a pending milestone. Sign in with OTP (`POST /api/v1/auth/otp/request`, then `/auth/otp/verify`; locally the code is printed in `docker compose logs api`) as:
   - the client `adaeze.client@example.com`
   - the contractor `+2348030000001`
   - ops `+2348030000004`

   Then:
   - client: `POST /projects` with `"contractor_phone": "+2348030000001"`
   - client: `PUT /projects/{id}/site`
   - contractor: `PUT /projects/{id}/boq`
   - client, contractor and ops: `POST /projects/{id}/boq/approve`

   The project is now `active`. Take a milestone id from `GET /projects/{id}/boq`. The Swagger UI at http://127.0.0.1:8000/docs ("Authorize" with each token) is the quickest way.
4. Start the funding:
   ```bash
   curl -s -X POST http://127.0.0.1:8000/api/v1/projects/$PROJECT/funding \
     -H "Authorization: Bearer $CLIENT_TOKEN" -H "Idempotency-Key: manual-1" \
     -H "Content-Type: application/json" -d "{\"milestone_id\":\"$MILESTONE\",\"currency\":\"GBP\"}"
   ```
5. Open `checkout_url` and pay with card **4242 4242 4242 4242**, any future expiry, any CVC and postcode.
6. The `stripe listen` window shows `checkout.session.completed → 200`. Then check:
   - `docker compose exec db psql -U ibackhome -c "select status, funded_at from milestones where id='$MILESTONE'"` shows `funded`.
   - `... -c "select transaction_id, account, direction, amount_minor, currency, fx_rate from ledger_entries order by created_at desc limit 7"` shows the 7 rows from section 3.
   - `GET /api/v1/ops/audit` (as ops) lists `escrow.funded`.
7. Re-send the event (`stripe events resend evt_...`). The answer is `"duplicate": true` and nothing changes.

`stripe trigger checkout.session.completed` still works for a quick signature check, but its session isn't one of ours (no funding metadata), so it is stored and ignored.

## 8. Decisions, deviations from the spec, limitations

- **New tables, for the team to agree:** `payout_recipients` and `payouts` aren't in the spec. `suppliers.paystack_recipient_code` (spec) can point at `payout_recipients.recipient_code` once suppliers exist. Proposed spec addition: both tables as in section 6, owned by base/payments.
- **No bank-details endpoint yet (decision):** `register_payout_recipient` is a service function only. The onboarding screens (web phase) decide the shape, and the endpoint should first check the account name with Paystack's resolve API (`GET /bank/resolve`) so a typo can't send money to a stranger. Proposed later: `POST /payout-recipients` (contractor, supplier) and `GET /banks`.
- **Funding uses the escrow feature's folder** (spec: escrow = "funding, release, disputes"); FX, fees, Stripe and Paystack clients live in `base/payments`.
- **Unmatched payments:** if money arrives for a milestone that is no longer `pending` (two checkout tabs), belongs to another project, or the amount disagrees with the quote, only T1 is written, gross to `client_funding`. That keeps our ledger equal to Stripe. There is no hold, and an audit `funding.unmatched` is written for ops to refund. A refund flow doesn't exist yet.
- **A partner that confirms holds later** (`HoldResult.status == "pending"`): T1 only, with audit `funding.hold_pending`. T2, T3 and `mark_funded` wait for the partner's confirmation webhook, which arrives with a real partner. `SimulatedEscrow` always answers `held`.
- **The webhook trusts Stripe's signed metadata** for the rate and amounts the client was quoted, and re-checks them against the milestone and the paid total.
- **`checkout.session.completed` with `payment_status` other than `paid`** is stored and ignored; `checkout.session.async_payment_succeeded` funds it later.
- **Limitations:**
  - `SimulatedEscrow` keeps holds in memory, so restarting the API forgets them. The ledger keeps everything.
  - If Paystack accepts a transfer but our answer is lost, our retry sees Paystack's "duplicate reference" refusal. A follow-up should check `GET /transfer/verify/{reference}` before retrying.
  - Tests check balance in Python on the rolled-back test session. The database's deferred balance trigger (Day 1) also guards every real commit.
  - `stripe_clearing` → partner settlement entries come with reconciliation.

## 9. What's next

- **Day 4:** real `request_release` (escrow release + ledger `contractor_payable` / `escrow`), the release confirmation webhook, and supplier payment through `initiate_transfer`. Payout ledger entries: debit `escrow_payouts`, credit `contractor_payable` on `transfer.success`.
- **Then:** `GET /projects/{id}/ledger` (client, ops), a refund path for `funding.unmatched`, and the bank-details endpoint once the web phase starts.
