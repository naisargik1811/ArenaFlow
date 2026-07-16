# ArenaFlow

GenAI for the **FIFA World Cup 2026** — stadium operations and the fan
experience, on one small model.

## Chosen vertical

Event-day operations and fan engagement for a mega-event. Two surfaces,
one model:

- **Fan Concierge** (`/fan`) — multilingual chat. Fans ask about
  transit, accessibility (sensory rooms, hearing loops, ASL screens, step-free
  routes), gates, sustainability, or arrival timing. Replies are grounded in
  a curated knowledge base of every host city.
- **Operations Dashboard** (`/ops`) — live gate waits, transit load,
  weather and AQI, plus an AI co-pilot for staff ("what next?").

The operational hook: a synthetic but deterministic **live snapshot** per
venue/minute drives the ops view, and the same RAG layer powers both
surfaces. The point of the build is a *robust, cheap, demo-proof*
service: it must work with **no API key**, survive malformed model
output, and never leak fan data.

## Approach and logic

**One source of truth for the model.** The caller never branches on
online/offline. `fan_reply` / `ops_reply` always return the same
`Reply` shape (`text`, `source`, `model`, `used_ids`); on any
failure they fall back to a deterministic template. That single seam keeps
every route, test, and the UI identical whether the LLM is reachable or not.

**RAG with zero extra dependencies.** The retriever is a stdlib-only
TF-IDF-ish cosine over tokenised snippets (~16 curated facts).
For this KB size a vector DB is pure tax, so it is deliberately absent.
Retrieval is city-scoped: a query filtered to `"Toronto"` only ever
returns Toronto snippets, so answers can't cross-contaminate between venues.

**Offline-first fallback.** With no `NVIDIA_API_KEY` (or any network /
shape error) the LLM call is skipped and a templated answer is returned.
This is not a degraded mode — it is the default safe path, so the app is
useful in a locked-down or offline environment and can't be taken down by
an API outage.

**Deterministic synthetic ops state.** `snapshot(venue, minute)` is seeded
by `f"{venue}-{minute}"`, so the same venue+minute always yields the
same inside-count, weather, gates and alerts. That makes the co-pilot
reproducible and the behaviour testable, while still looking live.

**Security by default.** Every response carries a Content-Security-Policy
(`script-src 'self'`, `frame-ancestors 'none'`), `X-Content-Type-Options`,
`X-Frame-Options: DENY`, and `Referrer-Policy`. The frontend renders
all model/fan text with `textContent` (never `innerHTML`), so a prompt
injection or XSS payload can never become executable HTML. **No fan data
is stored** — every request is self-contained.

## How the solution works

```
arenaflow/
  main.py        App factory; serves pages + /api; defensive headers (async dep)
  config.py      Settings from env (NVIDIA_API_KEY, NVIDIA_MODEL)
  api/
    routes.py   GET /api/health|/venues|/cities|/ops/snapshot
                POST /api/fan/ask | /api/ops/ask   (all async)
    schemas.py  Pydantic request/response models + whitespace guards
  core/
    llm.py         NVIDIA NIM (OpenAI-compatible) client + offline fallback
    retriever.py   stdlib TF-IDF cosine, city-scoped
  data/
    kb.py          Curated venue / accessibility / policy snippets
    ops.py         Deterministic synthetic live snapshot
  static/        index/fan/ops HTML + CSS + JS (textContent-only)
tests/            unittest + pytest (94 cases, <0.1s)
```

- **Request path is fully async and thread-pool-free.** Route handlers and
  the security-header dependency are `async`; the LLM uses
  `httpx.AsyncClient`. Nothing in a request touches a worker thread, so
  the service is non-blocking and won't deadlock under any ASGI transport.
- **LLM client** `POST`s to `integrate.api.nvidia.com/v1/chat/completions`
  with a 12s timeout. The completion text is validated (empty / whitespace
  responses are rejected) and on any `httpx` error, `ValueError`,
  `KeyError` or `IndexError` it falls back to the template.
- **Frontend** is static; pages are read once at startup and served from
  memory (no per-request file I/O). The JS fetches `/api/*` same-origin
  and renders results with `textContent`.

### Run it

```bash
cd ArenaFlow
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # optional: set NVIDIA_API_KEY for the live model
python -m arenaflow.main    # http://localhost:8000
```

### Tests

```bash
python -m unittest discover -s tests -v     # OR: pytest
```

94 tests cover input boundaries (422/404), city scoping (no cross-venue
leakage), snapshot invariants (inside ≤ capacity, deterministic, valid gate
shape), language detection, offline fallback on every error mode, the live
LLM path, injection/XSS payloads, and security headers on every route.

## Challenge alignment (Smart Stadiums & Tournament Operations)

ArenaFlow is a GenAI assistant for **FIFA World Cup 2026** fans, volunteers,
and venue staff. It maps directly onto the brief's target outcomes:

- **Navigation & transportation** — fans ask transit/gate questions; the
  retriever grounds answers in per-venue snippets (nearest metro, drop-off,
  gate locations) and the city-scoped fallback keeps answers venue-correct.
- **Accessibility** — sensory rooms, hearing loops, step-free routes and
  mobility guidance are first-class KB facts, surfaced to fans and to staff
  co-pilot prompts.
- **Multilingual assistance** — `detect_language` sets the reply language
  (es/fr/de/pt/it/ja/ko/ar/ru + English); the Fan Concierge answers in the
  fan's own language with no extra model call.
- **Crowd management / operational intelligence** — the Operations Dashboard
  shows live (deterministic) gate waits, transit load, weather and AQI, and
  an AI co-pilot turns that snapshot into a "what next?" recommendation.
- **Real-time decision support** — staff get a grounded, source-cited reply
  from the same RAG layer fans use, so recommendations trace back to the
  live snapshot and KB.
- **Sustainability** — KB snippets carry transit and accessibility guidance
  that shifts fans to public transport and reduces venue friction.
- **Real signal, not just synthetic** — `transit_status()` in `data/ops.py` reads a live feed when `ARENAFLOW_LIVE_TRANSIT_URL` is set and falls back to the deterministic source on any error, so operational intelligence can ingest a real transit API without breaking the offline-first, demo-proof default.
- **Robust by design** — offline-first fallback, validated model output, and
  CSP/XSS-safe rendering mean the service stays useful and safe during a
  match-day API outage or a malicious prompt.

## Assumptions

- **One small model is enough.** Default `meta/llama-3.1-8b-instruct`;
  override via `NVIDIA_MODEL`. The NIM endpoint is OpenAI-compatible.
- **The knowledge base is curated and static.** Real deployment would back
  `venue_cities()` / `all_snippets()` / `snapshot()` with live feeds; the
  seams are already there.
- **The ops snapshot is synthetic** for the demo. The route is a real
  1-call-per-page view a match-day integration would back with gate counters
  and transit APIs.
- **No fan PII is stored or logged.** Requests are stateless.
- **For production/public exposure** the app must sit behind a reverse proxy
  (Caddy/nginx) with TLS and **rate limiting**, and the `/api/*` routes
  should be gated (API key / origin allowlist) so a random site can't
  drive your paid NVIDIA quota. The app binds `0.0.0.0` and is safe
  to expose *behind* such a proxy, but it ships without built-in auth or
  rate limiting by design (it is a demo).

## Environment note

This repository was developed in a network-restricted sandbox, so the public
GitHub push is performed by the operator; the code, tests, and this README
are complete and committed locally, ready to push.
