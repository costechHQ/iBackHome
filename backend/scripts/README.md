# scripts/

Owner: James.

- `seed.py` — fills a fresh database with one user per role, two Enugu projects, one ops user per AI agent, a verified supplier, and Paystack bank accounts for the contractor and supplier (real Paystack test mode when `PAYSTACK_SECRET_KEY` is set; a stand-in code locally; skipped elsewhere). Safe to run twice.
- `simulator.py` — creates evidence, claims and approvals on staging so the web and Flutter phases have realistic data (backend day 5).
