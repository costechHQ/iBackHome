# Day 1 — Double-entry ledger and escrow provider interface

Owner: Gabriel · Branch: `gabriel/day-01-ledger` · Spec: [Payments, escrow and ledger](../../spec.md#payments-escrow-and-ledger)

## 1. In one paragraph

iBackHome promises clients abroad that their money is only released when building work in Enugu has been verified, and that iBackHome itself never holds the money. Two pieces make that promise checkable. First, the **double-entry ledger**: every movement of money is recorded as a transaction whose debits equal its credits, in one currency. The database itself refuses to store anything else, even if our Python code has a bug. Rows can never be edited or deleted, so the history can't be quietly rewritten. Second, the **escrow provider interface**: one small contract (`hold`, `release`, `balance`) that the rest of the code uses to talk to the licensed escrow partner, with a simulated partner for local development, staging and the demo until a real one signs. Together they are the base for [FR-13](../../iBackHome%20%E2%80%94%20Product%20Requirements%20Document.md) (funding shows in the ledger; funds held by the partner), [FR-14](../../iBackHome%20%E2%80%94%20Product%20Requirements%20Document.md) (release only through the partner, after approvals) and [FR-23](../../iBackHome%20%E2%80%94%20Product%20Requirements%20Document.md) (every money movement recorded and impossible to edit), and they meet the PRD's "Money safety" requirement for a double-entry ledger.

## 2. How it works

**Writing to the ledger.** A feature (for example the Stripe webhook handler) builds a list of entries with `debit(...)` and `credit(...)` and calls `post_transaction`. Python checks the entries straight away and refuses bad ones with a clear error code. Good entries are added to the caller's open database transaction, but not committed. The caller then makes its other changes (milestone state, audit log) and commits once. At that moment Postgres runs a **deferred constraint trigger**, which re-adds the debits and credits of every transaction just written. If anything is off, the whole commit fails: ledger rows, state change and audit entry all roll back together.

Two guards, one for fast and friendly errors (Python) and one that cannot be bypassed (the database):

```mermaid
flowchart TD
    A["Feature code<br/>e.g. Stripe webhook handler"] -->|"debit(...), credit(...)"| B["post_transaction()<br/>Python checks"]
    B -->|"bad: fewer than 2 entries,<br/>mixed currency, amount ≤ 0,<br/>debits ≠ credits"| E1["AppError 422<br/>nothing written"]
    B -->|ok| C["INSERT rows into the caller's<br/>open DB transaction (no commit)"]
    R["Raw SQL / a future bug<br/>that skips the service"] -.->|INSERT| C
    C --> D["Caller also writes state change<br/>and audit log, then COMMIT"]
    D --> T{"Deferred trigger at COMMIT<br/>per transaction_id:<br/>debits = credits?<br/>exactly one currency?"}
    T -->|yes| OK["Committed"]
    T -->|no| E2["Commit fails<br/>everything rolls back"]
    U["UPDATE / DELETE / TRUNCATE"] -->|"trigger + REVOKE"| E3["Refused: append-only"]
```

**Talking to the escrow partner.** `features/escrow` code never imports a specific partner. It calls `get_escrow_provider()`, which reads the `ESCROW_PROVIDER` setting and returns an object that satisfies the `EscrowProvider` protocol. Today the only implementation is `SimulatedEscrow`; the real partner gets its own class later, and nothing outside `features/escrow` changes.

```mermaid
classDiagram
    class EscrowProvider {
        <<Protocol>>
        +hold(project_id, amount_minor, currency, ref) HoldResult
        +release(hold_ref, payee, amount_minor, ref) ReleaseResult
        +balance(project_id) Balance
    }
    class SimulatedEscrow {
        in-memory, deterministic
        idempotent on ref
        +fail_next(operation, times)
        +reset()
    }
    class RealPartnerEscrow {
        future: once a partner signs
    }
    class get_escrow_provider {
        reads ESCROW_PROVIDER
    }
    EscrowProvider <|.. SimulatedEscrow
    EscrowProvider <|.. RealPartnerEscrow
    get_escrow_provider ..> EscrowProvider : returns
```

`ref` is our idempotency key. Calling `hold` or `release` again with the same `ref` returns the first result and never holds or releases twice, which is what makes retries safe. Reusing a `ref` with different details is refused (409).

## 3. Worked example: a client pays £1,000

From the spec: a client pays £1,000 for the foundation milestone of project `P`. Amounts are in minor units (pence, kobo). The rate is an illustrative ₦2,050.50 per £1, stored as `Decimal("2050.5")`. All three transactions share `ref_type="payment_event"` and the same `ref_id`, which links the two halves of the conversion.

| Txn | `account` | `direction` | `amount_minor` | `currency` | `fx_rate` |
| --- | --- | --- | --- | --- | --- |
| T1 (payment received) | `stripe_clearing:GBP` | debit | 100000 | GBP | |
| T1 | `client_funding:P:GBP` | credit | 100000 | GBP | |
| T2 (converted out) | `client_funding:P:GBP` | debit | 100000 | GBP | |
| T2 | `fx_conversion:GBP` | credit | 100000 | GBP | |
| T3 (held in escrow) | `escrow:P:NGN` | debit | 205050000 | NGN | 2050.5 |
| T3 | `fx_conversion:NGN` | credit | 205050000 | NGN | 2050.5 |

In code:

```python
from decimal import Decimal
from app.base.payments import accounts, credit, debit, post_transaction

rate = Decimal("2050.5")
ref = {"ref_type": "payment_event", "ref_id": event.id}
await post_transaction(session, [debit(accounts.stripe_clearing("GBP"), 100_000, "GBP"),
                                 credit(accounts.client_funding(p, "GBP"), 100_000, "GBP")], **ref)
await post_transaction(session, [debit(accounts.client_funding(p, "GBP"), 100_000, "GBP"),
                                 credit(accounts.fx_conversion("GBP"), 100_000, "GBP")], **ref)
await post_transaction(session, [debit(accounts.escrow(p, "NGN"), 205_050_000, "NGN", rate),
                                 credit(accounts.fx_conversion("NGN"), 205_050_000, "NGN", rate)], **ref)
await session.commit()
```

What `balance()` returns afterwards (debits minus credits):

| Account | `balance()` | Meaning |
| --- | --- | --- |
| `stripe_clearing:GBP` | `100000` | £1,000 received through Stripe, not yet settled onward |
| `client_funding:P:GBP` | `0` | The client's £1,000 came in (−100000) and was converted out (+100000) |
| `fx_conversion:GBP` | `-100000` | £1,000 went into the conversion |
| `fx_conversion:NGN` | `-205050000` | ₦2,050,500 came out of the conversion |
| `escrow:P:NGN` | `205050000` | ₦2,050,500 held by the escrow partner for project P |

This example is a test: `test_worked_example_client_pays_1000_gbp` in [test_ledger_service.py](../../../backend/app/base/payments/tests/test_ledger_service.py).

## 4. Data model

New table **`ledger_entries`** ([models.py](../../../backend/app/base/payments/models.py), migration [20261011_1500_create_ledger_entries.py](../../../backend/alembic/versions/20261011_1500_create_ledger_entries.py)):

| Column | Type | Notes |
| --- | --- | --- |
| `id` | UUID | primary key (core base model) |
| `transaction_id` | UUID | groups the entries of one balanced transaction |
| `account` | varchar(200) | built with `accounts.*` helpers, always ends in the currency |
| `direction` | varchar(6) | `debit` or `credit` (CHECK) |
| `amount_minor` | BIGINT | `> 0` (CHECK); minor units, never floats |
| `currency` | varchar(3) | ISO 4217, `^[A-Z]{3}$` (CHECK) |
| `fx_rate` | NUMERIC(20,10), nullable | `> 0` when present; set on the converted leg |
| `ref_type` | varchar(50) | what caused it, e.g. `payment_event`, `escrow_release` |
| `ref_id` | UUID | id of that thing |
| `created_at`, `updated_at` | timestamptz | UTC (core base model). `updated_at` never changes because rows are append-only |

Indexes: `(ref_type, ref_id)`, `account`, `transaction_id`, `(created_at, id)` (for pagination).

Database objects: constraint trigger `ledger_entries_balanced` (deferred) → function `ledger_entries_check_balanced()`; triggers `ledger_entries_append_only` (UPDATE/DELETE) and `ledger_entries_no_truncate` → function `ledger_entries_reject_change()`; UPDATE, DELETE, TRUNCATE revoked from `PUBLIC` and from `LEDGER_APP_ROLE`.

No escrow tables yet (`escrow_accounts` arrives on day 2, `escrow_releases` on day 4).

## 5. Functions teammates can call

All in `app.base.payments` (re-exported from [service.py](../../../backend/app/base/payments/service.py)). Each takes the session first and **never commits**.

| Function | Who uses it |
| --- | --- |
| `post_transaction(session, entries: Sequence[Entry], *, ref_type: str, ref_id: UUID) -> UUID` | Gabriel (webhooks, funding, releases, payouts). Nobody else writes money. |
| `balance(session, account: str) -> int` | Gabriel (escrow), James (reports, reconciliation), web dashboards via `GET /projects/{id}/ledger` later |
| `list_entries(session, *, account=None, ref_type=None, ref_id=None, since=None, until=None, cursor=None, limit=50) -> EntryPage` | James (nightly reconciliation, report agent's `get_ledger`) |
| `debit(account, amount_minor, currency, fx_rate=None) -> Entry` / `credit(...)` | Anyone building entries |
| `accounts.stripe_clearing(cur)`, `client_funding(project_id, cur)`, `escrow(project_id, cur)`, `fx_conversion(cur)`, `contractor_payable(cur)`, `supplier_payable(cur)`, `escrow_payouts(cur)`, `fees(cur)` | Anyone naming an account |

`EntryPage` has `items: list[LedgerEntry]` (oldest first) and `next_cursor: str | None` (None on the last page). `since` is inclusive and `until` exclusive, both on `created_at`. `limit` must be 1–200.

Example (James, reconciliation):

```python
from app.base.payments import accounts, list_entries

cursor = None
while True:
    page = await list_entries(session, account=accounts.escrow(project_id, "NGN"),
                              since=yesterday, until=today, cursor=cursor, limit=200)
    for entry in page.items:
        ...  # compare with the partner's statement
    if page.next_cursor is None:
        break
    cursor = page.next_cursor
```

Escrow (internal to `features/escrow`, listed so reviewers know the contract) in [providers.py](../../../backend/app/features/escrow/providers.py):

```python
provider = get_escrow_provider()
hold = await provider.hold(project_id, 205_050_000, "NGN", ref=str(event.id))      # HoldResult
rel = await provider.release(hold.provider_ref, f"contractor:{user_id}", 50_000_000,
                             ref=str(release.id))                                   # ReleaseResult
bal = await provider.balance(project_id)                                            # Balance
```

| Type | Fields |
| --- | --- |
| `HoldResult` | `provider_ref`, `status` (`held` / `pending` / `failed`), `project_id`, `amount_minor`, `currency`, `ref` |
| `ReleaseResult` | `provider_ref`, `status` (`released` / `submitted` / `failed`), `hold_ref`, `payee`, `amount_minor`, `currency`, `ref` |
| `Balance` | `project_id`, `currency` (None if nothing held yet), `held_minor`, `released_minor`, `available_minor` |

Error codes: `escrow_invalid_amount` / `escrow_invalid_currency` / `escrow_invalid_payee` (422), `escrow_currency_mismatch` (422), `escrow_insufficient_funds` (422), `escrow_hold_not_found` (404), `escrow_ref_conflict` (409), `escrow_provider_unavailable` (502, safe to retry with the same `ref`).

## 6. Safety rules enforced

| Rule | Python (`post_transaction`) | Database |
| --- | --- | --- |
| At least two entries | ✓ `ledger_unbalanced` | implied: balanced + positive means ≥1 debit and ≥1 credit |
| Debits = credits per transaction | ✓ `ledger_unbalanced` | ✓ deferred constraint trigger, at commit |
| One currency per transaction | ✓ `ledger_mixed_currency` | ✓ same trigger |
| Amount is a positive integer | ✓ `ledger_invalid_amount` (also rejects floats, Decimals, `True`) | ✓ BIGINT + CHECK `amount_minor > 0` |
| Valid direction, ISO currency, account, Decimal fx_rate | ✓ `ledger_invalid_entry` | ✓ CHECKs on direction, currency, `fx_rate > 0` |
| Never edited or deleted | (no update/delete function exists) | ✓ triggers refuse UPDATE, DELETE, TRUNCATE for every role, plus REVOKE from the app role |
| One currency per account | ✓ helpers always add the currency; `balance()` raises `ledger_mixed_currency` | — |

**Why both?** Python gives callers an immediate, readable error before anything is written. The database is the guarantee: it also catches raw SQL, a future bug, a migration script, or a second service that never calls `post_transaction`. The deferred trigger runs at commit rather than per row, because a balanced transaction is unbalanced for a moment between its first and second INSERT. The append-only triggers exist because in local dev and CI the app connects as the table owner and a superuser, and Postgres does not apply REVOKE to them. The triggers work for every role.

## 7. How to run and test it locally

From `backend/`. The tests need a Postgres + PostGIS database migrated to head.

```bash
# Database: either Christopher's stack ...
docker compose up -d db                      # postgres+postgis on localhost:5432
# ... or a throwaway one if 5432 is taken
docker run -d --name ibackhome-test-db -e POSTGRES_USER=ibackhome -e POSTGRES_PASSWORD=ibackhome \
  -e POSTGRES_DB=ibackhome -p 5433:5432 postgis/postgis:16-3.4
export DATABASE_URL=postgresql+psycopg://ibackhome:ibackhome@localhost:5433/ibackhome  # if you used 5433

# Python 3.12 environment
uv venv --python 3.12 .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
uv pip install -r requirements-dev.txt

# Migrate, then test
alembic upgrade head
pytest -q app/base/payments app/features/escrow
ruff check app/base/payments app/features/escrow && ruff format --check app/base/payments app/features/escrow
mypy app
```

**Windows:** async psycopg can't use the default Proactor event loop, so a plain `alembic upgrade head` fails there. Until `alembic/env.py` handles it, run:
`python -c "import asyncio,sys;asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy());from alembic.config import main;main(argv=sys.argv[1:])" upgrade head`
The pytest suite already handles this itself.

To see the database guard yourself:

```sql
BEGIN;
INSERT INTO ledger_entries (id, transaction_id, account, direction, amount_minor, currency, ref_type, ref_id)
VALUES (gen_random_uuid(), '00000000-0000-0000-0000-000000000001', 'demo:a:GBP', 'debit', 100, 'GBP', 'demo', gen_random_uuid());
COMMIT;  -- ERROR: ledger transaction ... is unbalanced: debits 100, credits 0
```

The key tests, with what each proves:

- `test_database_rejects_unbalanced_write_at_commit`: raw SQL bypasses the service and the commit fails. Disabling the trigger makes this test fail, which was checked by hand.
- `test_database_rejects_service_transaction_tampered_before_commit`: an extra row slipped in after `post_transaction` is caught.
- `test_update_and_delete_refused_for_every_role`, `test_non_superuser_app_role_gets_permission_denied` and `test_app_role_has_no_update_or_delete_grant`: append-only.
- `test_upgrade_from_empty_and_downgrade_one_step`: the migration round trip, run in a scratch database.

## 8. Decisions, deviations from the spec, and limitations

- **Account names always include the currency** (`contractor_payable:NGN`, `fees:GBP`), where the spec writes bare `contractor_payable` and `fees`. One account then never mixes currencies, so `balance()` can't add naira to pounds.
- **Append-only triggers in addition to REVOKE.** The spec asks for "no UPDATE or DELETE grants for the app role". We do that, but CI and local dev connect as a superuser who owns the table, and grants don't apply to superusers, so the triggers make it real everywhere. Production should connect as a separate non-owner role (asked of Christopher).
- **Extra error codes** besides the three requested: `ledger_invalid_entry` (bad direction, currency, account, or a float `fx_rate`), `invalid_cursor` and `invalid_limit`.
- **`created_at` is the database transaction's start time**, so all entries committed together share a timestamp. Pagination breaks ties by `id`, so pages never skip or repeat rows.
- **The balance trigger is per row,** so it re-checks a transaction once per entry. That's trivial at pilot scale; a statement-level transition table would be the optimisation if volume grows.
- **REVOKE runs at migration time.** If `LEDGER_APP_ROLE` doesn't exist then, it's skipped with a notice; a role created later needs the REVOKE run again (or default privileges set by whoever creates it).
- **`SimulatedEscrow` keeps state in memory per process.** The API and the Celery worker don't share it, and a restart forgets holds. That's fine for unit tests and a single-process demo. Day 4 (releases via the `escrow.submit_release` Celery task) needs it persisted, probably in `escrow_accounts` / `escrow_releases` or Redis.
- **`ref` is a `str`** (we'll pass a UUID string). The spec left the types open.
- **The simulated partner allows one currency per project** (`escrow_currency_mismatch`).
- **The migration chains after `create_users_and_auth`,** the latest migration on `main`. A migration is only ever based on one that is already on `main`. James's `day-02-vetting` migration will need rechaining (or `alembic merge heads` by Christopher) once this merges.
- **No HTTP endpoints today.** `GET /projects/{id}/ledger` comes later, so there are no endpoint tests yet.

## 9. What's next

- **Day 2 (tomorrow): webhook safety.** This adds the `payment_events` table with unique `(provider, event_id)`, `record_event` / `mark_processed`, and signature checks for Stripe, Paystack and escrow. The webhook routes reject forged events and acknowledge duplicates without reprocessing them. Day 2 also adds the `escrow_accounts` table, plus a first, separate small PR with the `request_release(session, milestone_id, actor)` stub that **Lilian** needs for milestones.
- **Who depends on this:**
  - **James** uses `list_entries` and `balance` for reconciliation and for the report agent's `get_ledger`.
  - **Lilian**'s milestone `funded` / `released` transitions will be driven by ledger-writing handlers.
  - **Abigail**'s ops console will show ledger and escrow state.
  - **Christopher** owns the role, env-var and CI items listed in the PR.
