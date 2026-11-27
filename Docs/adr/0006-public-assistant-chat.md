# ADR 0006: A public chat assistant that answers from vetted text, costs nothing and stores nothing

- **Status:** Accepted (2026-11-27). Tier 1 (vetted answers) is built; tier 2 (a free language model) is optional, off by default and not built.
- **Date:** 2026-11-27
- **Owner:** Christopher (decision)
- **Spec edits:** the route `POST /assistant/chat` and one line in the AI agents section (both in this PR).

## Context

Visitors to ibackhome.com ask the same few questions (how escrow works, what it costs, how to become a supervisor,
how to reach us) and today the only answer is "write to us". We want a chat box on the home page and the Contact page
that answers automatically. Three constraints came from the product owner:

1. **It must cost nothing.** No paid model, no paid widget.
2. **It sits on a public page**, so anyone can call it: it must be cheap to abuse-proof, and must never reach real data.
3. **Nothing visitors type is stored.** Only counts.

A check of the free language-model tiers (Cloudflare Workers AI, Groq, Google Gemini) in November 2026 found that
each has a free allowance, but the daily limits are not stated consistently and can change, so a free quota is not a
foundation for a public feature. A model also drifts, can be manipulated by what a visitor types, and sends that text to
a third party.

## Decision

**1. Vetted answers first (tier 1, always on when the assistant is enabled).**

- `backend/app/features/assistant/` holds about 30 to 40 curated entries: example questions, keywords, and an answer
  written and approved by us. A visitor's text is matched to the best entry with plain Python (lower-case, stop words
  removed, weighted keyword and phrase overlap, a confidence threshold). No model, no API key, no third party; instant
  and deterministic, so it cannot invent facts or be talked into a promise.
- Below the threshold, and for anything about a person's own account, payment or dispute, the answer is a **handoff**:
  "I can't answer that here" plus the contact options (email, WhatsApp).
- **Numbers come from data, never from text or a model.** An answer uses placeholders (`{plan_premium_price}`,
  `{funding_fee}`, ...) filled at request time from the subscription plans and the funding fee setting, through their
  `service`/module APIs. A price change is picked up with no edit to the answers. A test fails if an entry contains a
  number that is not a placeholder.
- **Honesty about money.** Entries say the product is in a pilot, payments run in test mode and no real money is held
  yet, and that we are working with banks to become the licensed escrow partner. No entry may say a partner is already in place or pays out.

**2. An optional free model (tier 2, `ASSISTANT_MODEL_ENABLED=false` by default).**

- Only when tier 1 has no confident match, the existing `LLMClient.generate()` (`features/agents/llm.py`) may answer
  from the same entries. The key must be a Google AI Studio key with **no billing account attached**, so it cannot be
  charged; when its free quota runs out the call returns 429 and we hand off.
- Tool-less, no database access, output length capped, plain text only, its own daily cap below the free quota.
- Not needed at launch. Switching it on means accepting that Google's free tier may use submitted text to improve its
  products (to confirm in Google's terms), and adding one sentence to the privacy policy.

**3. Guardrails in code.**

- Per-IP limit (default 10 questions per 10 minutes) and a global daily cap, counted in Redis (counters expire by
  themselves, no table): over a limit is 429 `rate_limited` and the page shows the contact options.
- Message at most 500 characters; extra request fields refused; answers are plain text (no HTML, no links we did not
  write); the route accepts `Idempotency-Key`.
- **Nothing typed is stored.** Only counters in the logs (answered, handed off, limited, failed), never the text and
  never an IP address in clear.
- No tools and no access to users, projects or money. This is not the logged-in WhatsApp assistant in the spec, which
  is a separate feature with scoped tools.
- Off until `ASSISTANT_ENABLED=true`.

**4. Where it appears.** A floating button on the home page and the Contact page only (a panel, full-screen on phones).
It says it is automated and may be wrong, and asks people not to share passwords, a NIN or bank details. "Talk to a
person" is always visible.

## Consequences

- No running cost and no new vendor at launch; the only per-use cost is a little CPU and a Redis counter.
- The assistant can only say what we wrote, which is the point, and also its limit: a new topic needs a new entry.
  Entries are public statements, so each one needs the product owner's approval before it ships.
- Public pages already say "a licensed escrow partner holds your money" while escrow is simulated. The assistant will
  use the pilot wording above, so the website copy and the assistant must be brought into line (separate decision).
- A new unauthenticated POST route: abuse protection is part of the feature, not an afterthought.
- If tier 2 is ever switched on, the privacy policy must say that typed questions are sent to Google to produce an
  answer.

## Alternatives considered

- **A paid model or a paid chat widget (Intercom, Tidio).** Ruled out: cost, and visitor data leaving in ways we have not reviewed.
- **A free language model as the main engine.** Limits unclear and changeable; answers can drift or be manipulated;
  text goes to a third party. Kept only as the optional tier 2.
- **Our own model on the Contabo server.** Takes memory from the live site and is slow on a CPU-only server.
- **An agent that calls our API.** A public visitor must never reach real data.
- **Saving conversations to improve answers.** Declined for now; can be added later with a table, a 30-day deletion job
  and a privacy-policy line.

## Open decisions

1. The exact wording of each answer entry (draft in `Docs/proposals/assistant-answers.md`) and the pilot/escrow wording.
2. Whether and when to switch tier 2 on, and the privacy-policy sentence that goes with it.
3. Whether the public website copy about escrow should also be changed to the pilot wording (the escrow partner is being sought among banks).
