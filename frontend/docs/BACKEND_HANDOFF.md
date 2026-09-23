# Backend handoff

For the teammate building the backend, the multilingual AI and the RAG pipeline.

Everything you need to know to plug in without touching a single screen.

---

## The one-line version

The app currently runs entirely on a mock backend bundled inside it. When your API is up:

```bash
# .env
EXPO_PUBLIC_USE_MOCK_API=false
EXPO_PUBLIC_API_BASE_URL=https://your-api.example.com
```

That is the whole integration. No screen, component or hook changes.

## What you own

| Surface                             | Endpoint                        | Why it matters                          |
| ----------------------------------- | ------------------------------- | --------------------------------------- |
| **Multilingual AI assistant**       | `POST /v1/assistant/query`      | The "multi-lingual queries" requirement |
| **AI scheme recommendation**        | `POST /v1/recommendations`      | Requirement R1 — the headline feature   |
| **Scheme catalogue**                | `GET /v1/schemes`               | 5 of 8 verified; 3 flagged (see below)  |
| **Partner directory + fund health** | `POST /v1/partners/search`      | Requirement R3 — the whole routing rule |
| **Speech-to-text**                  | `POST /v1/assistant/transcribe` | Not yet consumed; unblocks voice input  |

Full request/response shapes: **`docs/API_CONTRACT.md`**.
Machine-readable truth: **`src/api/contracts/*.ts`** (Zod).

## Suggested order

Each step is independently shippable — the app keeps working on mocks for everything you
haven't done yet.

1. **`GET /v1/health`** — proves connectivity.
2. **`GET /v1/schemes`** — pure data, no AI. Gets a real catalogue in front of users fastest.
3. **`POST /v1/partners/search`** — needs the partner master plus fund-health data.
4. **`POST /v1/recommendations`** — the AI one. A working baseline already exists in
   `src/features/recommender/ruleEngine.ts`; read it first.
5. **`POST /v1/assistant/query`** — the RAG pipeline.
6. Streaming and transcription — v1.

## Three things the contract asks of you that are easy to miss

**1. Every response is validated.** The client parses each response with Zod and rejects
anything that does not match, with a `ContractViolationError` naming the failing fields. A
response that is _nearly_ right fails. Test against the schemas, not against your own
assumptions about them.

**2. Recommendations must explain themselves.** `reasons[]` is rendered as a prominent "Why
this scheme?" card, and `nearMisses[]` explains why someone was excluded. Financial literacy
is the stated problem in the brief — a bare ranked list does not meet it. `citations[]` from
your RAG layer is what makes an answer auditable.

**3. Partner eligibility is your judgement, not the client's.** The client renders
`eligibility.status` and never re-derives it from NPA numbers. `onlyAccepting` defaults to
true, so a partner you mark `NOT_ACCEPTING` will simply not be shown — which is the point of
requirement R3. When that filter empties the list, return everything with
`fallbackUsed: true` so the app can warn rather than dead-end.

## Data that needs replacing

Both files carry loud headers stating exactly what is known about each record. Read those
headers before changing anything — the labels are load-bearing, not decoration.

**`src/api/mock/fixtures/schemes.ts`** — eight schemes. **Five are verified** against
`nsfdc.nic.in/scheme` (checked 2026-09-07) and carry citations with `verified: true`. **Three
carry `verified: false`** — NSFDC lists them, but their current limits, rates, tenures and
moratoria could not be read from an official page, so the app shows its unverified-data
warning on them. Verify per scheme and flip `verified: true` individually, never all at once.
Two further schemes (Mahila Kisan, Shilpi Samridhi) were removed because sources conflicted on
whether they are still open.

⚠️ **Third-party aggregators contradict NSFDC and each other** — Term Loan quoted at 9–10%
against the official 8%, Micro Finance at ₹60,000 against ₹1.25 lakh, apparently from
pre-01.10.2023 figures. Only `nsfdc.nic.in` counts. Do not overwrite a verified figure with an
aggregator's.

**`src/api/mock/fixtures/partners.ts`** — five State Channelizing Agencies whose **names and
role are verified**. Coordinates are city-level, not the exact office. No phone number appears
unless the organisation publishes it, and **no NPA or fund-utilisation figure appears at all**.
Every record is `status: 'UNKNOWN'`. This needs the real SCA/PSB/RRB/NBFC-MFI master (37 SCAs
plus 55 further CAs) and a fund-health feed.

**The eligibility norms are already encoded** — per partner type, in
`src/features/partners/eligibilityNorms.ts`. They are not one threshold: an RRB may carry a
net NPA up to 15% while an NBFC-MFI must stay below 0.5%. `requiredInputsFor(type)` returns
the exact field list a feed would have to supply for each type. That function is the ask for
NSFDC — start there rather than designing a shape from scratch.

Settled: there is **no public source** for per-partner NPA or fund utilisation. NSFDC
publishes the rules, not the figures. Until a feed exists, `UNKNOWN` is the correct value and
must not be replaced with a modelled score.

## Language handling

Six languages: `en, hi, mr, bn, ta, te`.

- Every AI request carries `responseLanguage`. **Answer in it.** A user may type Hindi while
  the UI is Tamil; the answer follows the UI, not the query.
- `detectedQueryLanguage` is optional but useful for analytics.
- Scheme content uses `LocalizedText` maps (`{en: "...", hi: "..."}`) rather than i18n keys,
  because the catalogue is data, not UI copy. **`en` is mandatory** — it is the fallback
  everywhere.
- Adding a seventh language means updating `LanguageCodeSchema` on both sides.

## The voice pipeline

`app/voice.tsx` implements this end to end:

```
VOICE UI → Speech-to-Text → "text query" → POST /v1/assistant/query
         → ChatResponse → Text-to-Speech
```

Both `app/voice.tsx` and `app/assistant.tsx` run it — the voice screen sends the
transcript immediately, the chat screen drops it into the composer to be edited first.

Stages 3–6 are live today against the mock. Stage 2 is a provider abstraction in
`src/features/voice/speechToText.ts`:

| Provider  | Status                                                                               |
| --------- | ------------------------------------------------------------------------------------ |
| `web`     | **Working.** Web Speech API — no backend, Chrome and Safari, all six `-IN` locales   |
| `backend` | **Yours.** `POST /v1/assistant/transcribe`, contract in `src/api/contracts/voice.ts` |
| `none`    | Native without a dev build; the screen explains and offers typing                    |

⚠️ **`detectProvider()` will not claim the `backend` provider until you ship the endpoint.**
When it does not resolve, the screen says why rather than drawing a microphone that cannot
listen — see ADR-010 and ADR-019. Tell us when `/v1/assistant/transcribe` is live and we flip it on;
please don't ask us to enable it in advance.

`TranscriptionResponse.confidence` is worth populating. Below a threshold the client shows the
transcript for confirmation instead of sending it straight on — a misheard question about a
loan is worth one extra tap.

### ⚠️ Endpoint naming — please settle this

Your pipeline diagram calls the chat stage **`/v1/chat`**. This repo's contract has always
called it **`POST /v1/assistant/query`** (see [`API_CONTRACT.md`](API_CONTRACT.md) and
`src/api/contracts/assistant.ts`). Same endpoint, two names. Pick one and change the contract —
do not let the client alias it, or the next person reads two names for one thing.

## RAG suggestions

Grounding corpus worth indexing: NSFDC scheme circulars and guidelines, the Channel Partner
directory, eligibility criteria and document checklists, and an FAQ on the channel-finance
process (people mostly do not know they cannot apply directly).

### ⚠️ Read this before you crawl nsfdc.nic.in

**NSFDC's entire `/en/` tree returns 404.** Verified 2026-09-07:

```bash
for u in /scheme /en/allocation-of-funds /en/stand-up-india /en/eligibility-criteria; do
  curl -s -o /dev/null -w "%{http_code}  $u\n" -L "https://nsfdc.nic.in$u"
done
```

→ `200`, `404`, `404`, `404`. Also dead: `/en/channel-partners-scas`,
`/en/channel-partners-rrb`, `/en/schemes-to-be-implemented-through-nbfc-mfis`, and
`/UploadedFiles/other/2024-03-05/psb.pdf`.

Search engines still index every one of those URLs, so a sitemap- or SERP-driven crawl
produces a clean-looking list that all 404 — and an ingestion run that looks successful while
building a corpus of error pages.

**All of it is in the Wayback Machine, intact.** Resolve each page first:

```bash
curl -s "https://archive.org/wayback/available?url=nsfdc.nic.in/en/allocation-of-funds"
```

then crawl the returned snapshot URL. Prefer `nsfdc.nic.in/scheme` where it overlaps — that
one is still live. Every partner prudential norm in
`src/features/partners/eligibilityNorms.ts` was recovered this way and carries its capture
date; reuse those URLs rather than rediscovering them.

Two behaviours the UI already supports and rewards:

- `grounded: false` when you are not confident — the app shows "please confirm with a Channel
  Partner". That is a much better failure than a confident wrong answer about someone's loan.
- `suggestedActions[]` hand the user back into the app (open the calculator pre-filled, start
  the recommender, open a scheme). They render as tappable chips.

## What still ships in backend mode

Setting `EXPO_PUBLIC_USE_MOCK_API=false` routes every call to your API — verified by building
with the flag off, which succeeds and produces a working bundle. But the mock **data** is
still inside that bundle, and you should know why before it surprises you.

Each service statically imports its mock counterpart:

```ts
import { mockListSchemes } from '@/api/mock/server'; // ← unconditional import

export async function listSchemes() {
  if (USE_MOCK_API) return mockListSchemes(); // ← runtime branch
  return apiRequest(ENDPOINTS.schemes.list, SchemeListResponseSchema);
}
```

`USE_MOCK_API` is a runtime boolean, so Metro cannot drop the unused branch. Building with the
flag off and grepping the Hermes bundle still finds `MPBCDC`, `TAHDCO`, `nsfdc-term-loan` and
the rest.

**This is not a bug and nothing behaves wrongly** — every request goes to your server. It costs
a small amount of bundle size, and it means the fixtures are a genuine offline fallback if we
ever want one. If you would rather it were stripped, that is a deliberate change (conditional
`require`, or a Metro resolver alias), not an oversight — raise it and we will do it.

The practical consequence for you: **a stale fixture cannot mask a broken endpoint**, because
the mock branch is never reached with the flag off. If a screen looks right against your API,
it is your data.

## Testing against the real client

```bash
git clone <this repo> && cd sahaay-setu && npm install
cp .env.example .env      # set EXPO_PUBLIC_USE_MOCK_API=false and your base URL
npm start
```

Press `a` for Android or `i` for iOS, or scan the QR with Expo Go. If a response breaks the
contract you will see a `ContractViolationError` naming the exact fields — that message is the
fastest debugging tool you have here.

To compare your recommendation output against the deterministic baseline, flip
`EXPO_PUBLIC_USE_MOCK_API` back to `true` and run the same profile through the wizard.
