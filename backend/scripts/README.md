# scripts/

Owner: James.

- `seed.py` — fills a fresh database with one user per role, two Enugu projects, one ops user per AI agent, a verified supplier, and Paystack bank accounts for the contractor and supplier (real Paystack test mode when `PAYSTACK_SECRET_KEY` is set; a stand-in code locally; skipped elsewhere). Safe to run twice.
- `load_checklists.py` — loads ops' milestone checklists (one per kind of milestone: Foundation, Roofing, ...) from a Markdown file of `## headings` and `- items`. It only checks the file unless you add `--apply --as <ops phone or email>`; it saves everything or nothing, and is safe to run twice. The wording is ops', so nothing is built in. See the top of the file.
- `simulator.py` — creates evidence, claims and approvals on staging so the web and Flutter phases have realistic data (backend day 5).
