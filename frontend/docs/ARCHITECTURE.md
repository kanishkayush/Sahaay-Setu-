# Architecture

## The shape of the thing

```
┌──────────────────────────── app/ (expo-router) ────────────────────────────┐
│  onboarding/  ·  (tabs)/  ·  recommend/  ·  scheme/[id]  ·  partner/[id]   │
│                     ·  assistant  ·  voice                                 │
│                          screens only — no business logic                  │
└────────────────────────────────────┬───────────────────────────────────────┘
                                     │
                    ┌────────────────┴────────────────┐
                    │                                 │
         ┌──────────▼──────────┐          ┌───────────▼───────────┐
         │  src/hooks/         │          │  src/features/        │
         │  React Query,       │          │  pure logic:          │
         │  device capability, │          │  EMI math,            │
         │  speech sessions    │          │  rule engine,         │
         └──────────┬──────────┘          │  partner norms,       │
                    │                     │  speech providers     │
         ┌──────────▼──────────┐          │  (no React, no I/O)   │
                                          └───────────────────────┘
         │  src/api/services/  │
         │  the only data door │
         └──────────┬──────────┘
                    │
       ┌────────────┴────────────┐
       │ USE_MOCK_API ?          │
       │                         │
┌──────▼───────┐        ┌────────▼────────┐
│ src/api/mock │        │ src/api/client  │──→ backend (separate repo)
│ in-memory    │        │ fetch + Zod     │
└──────────────┘        └─────────────────┘
```

Everything a screen renders arrives through `src/api/services/`. There is exactly one place
that calls `fetch` (`src/api/client.ts`) and exactly one switch that decides mock vs real
(`USE_MOCK_API`). That is what makes backend integration a one-line change.

## Why a mock backend ships inside the app

The backend and the AI/RAG pipeline are built by a different person, in parallel. Three
things follow from that:

- **Frontend work never blocks on backend availability.** Every screen was built and verified
  against the mock.
- **The app demos with no server and no internet.** On a conference floor that matters.
- **Integration is a config change**, not a refactor: set `EXPO_PUBLIC_USE_MOCK_API=false`.

The mock lives in `src/api/mock/` and mirrors the endpoint list in `src/api/endpoints.ts`
one-for-one. Every new endpoint gets a mock in the same commit.

## Why the contract is Zod, not TypeScript interfaces

Interfaces vanish at runtime. When two people build two halves of a system in parallel, the
failure you actually get is the backend returning a slightly different shape and the app
rendering `undefined` three screens deep, with a stack trace pointing nowhere useful.

`src/api/contracts/` holds Zod schemas. `apiRequest()` parses every response through the
schema for that endpoint. A drift throws `ContractViolationError` at the network boundary,
naming the path and the offending fields.

The schemas are also the documentation — `docs/API_CONTRACT.md` is prose around them.

## Two engines, on purpose

The Smart Scheme Recommender exists twice:

|         | On device                                | Backend                        |
| ------- | ---------------------------------------- | ------------------------------ |
| Where   | `src/features/recommender/ruleEngine.ts` | `POST /v1/recommendations`     |
| How     | deterministic rules                      | AI + RAG over scheme documents |
| Returns | `source: 'RULE_ENGINE'`                  | `source: 'AI'` or `'HYBRID'`   |

This is not redundancy waiting to be deleted (ADR-004):

- **Connectivity.** The target user often has none. The core feature must still work.
- **Accountability.** Public money, vulnerable users. Any AI recommendation can be diffed
  against a deterministic answer, and a disagreement is a signal worth investigating.

`recommendation.service.ts` calls the backend and falls back to the rule engine on failure,
flagging the result `offline: true` so the UI can say so.

## State: two kinds, kept apart

| Kind         | Where                  | Persisted       | Examples                                   |
| ------------ | ---------------------- | --------------- | ------------------------------------------ |
| Server state | React Query            | in-memory cache | scheme catalogue, partner search           |
| Device state | zustand + AsyncStorage | yes             | language, applicant profile, saved schemes |

The store is deliberately tiny. If something can be re-fetched, it does not belong there.

## Offline behaviour

| Feature               | Works offline?                                                    |
| --------------------- | ----------------------------------------------------------------- |
| EMI calculator        | Yes — pure math, no network by design                             |
| Scheme recommendation | Yes — falls back to the on-device rule engine                     |
| Scheme catalogue      | Yes if previously loaded (cached 1 hour)                          |
| Partner search        | No — needs live fund-health data                                  |
| AI assistant          | Degrades to the offline knowledge base, flagged `grounded: false` |
| Text-to-speech        | Yes — expo-speech runs on-device                                  |
| Speech-to-text        | No — the Web Speech API needs a network round-trip                |

## Privacy

The recommender asks for project type, cost, family income, education, and optionally gender.
That is all. No name, no Aadhaar, no PAN, no certificate numbers, no phone number.

Everything stays on the device. The profile is sent to the backend only as a request body,
never persisted server-side in v0. Location is requested when the user taps "Use my location"
and never on app start.

This is a deliberate choice (ADR-011): none of that data is needed to recommend a scheme, and
collecting government IDs from this population creates real risk for no product benefit. The
actual application happens in person at the Channel Partner.

## Accessibility as a constraint, not a polish pass

The users are often first-time smartphone owners on cheap devices in bright sunlight. So:

- Touch targets never below 48dp
- Body text never below 16px
- Contrast at or above WCAG AA
- Status never conveyed by colour alone — always paired with an icon or label
- Steppers rather than drag sliders (ADR-007)
- Indic-aware line heights in the shared `Text` component — Latin-tuned leading clips
  Devanagari, Bengali, Tamil and Telugu

## Voice

Both `app/voice.tsx` and `app/assistant.tsx` run one pipeline:

```
VOICE UI → Speech-to-Text → "text query" → POST /v1/assistant/query
         → ChatResponse → Text-to-Speech
```

It follows the same layering as everything else — a screen renders state, a hook owns the
session, and `src/features/voice/` holds the providers. Screens never touch the STT or TTS
modules directly, for the same reason they never call `fetch`.

Speech-to-text is **capability-detected at runtime**, not assumed. `detectProvider()` returns
the working provider or an explicit reason it has none, and the mic is rendered only when one
exists. That enforces ADR-010's rule — a microphone that does nothing is worse than none — in
code rather than by leaving the feature out. `POST /v1/assistant/transcribe` is contracted for
native but deliberately not claimed until it exists.

## Known limitations

See `context/state.json → next` and `openQuestions` for the live list. As of 2026-09-08:

|                                     |                                                                                                                                |
| ----------------------------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| **No test suite**                   | `emi.ts` and `ruleEngine.ts` are pure and were verified by throwaway scripts. They should be real tests.                       |
| **3 of 8 schemes unverified**       | MSY, LVY and GBS carry `verified: false`; their `nsfdc.nic.in` pages 404 to an automated fetcher.                              |
| **No per-partner fund data**        | NSFDC publishes the norms, not the figures, so every partner is `UNKNOWN`. Needs a feed — this one the app cannot solve alone. |
| **mr/bn/ta/te not native-reviewed** | Complete and AI-translated; each records `reviewStatus` in its `_meta`.                                                        |
| **Speech-to-text is web-only**      | Native needs a dev build or the backend endpoint. Absent, not broken, everywhere else.                                         |
| **Partner directory is partial**    | Five verified State Channelizing Agencies of 37, plus 55 further CAs.                                                          |
