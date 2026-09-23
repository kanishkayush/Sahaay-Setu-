# API Contract

**Source of truth: `src/api/contracts/*.ts`.** Those Zod schemas are what the client actually
validates against. This document is prose around them — if the two disagree, the schemas win.

Base URL comes from `EXPO_PUBLIC_API_BASE_URL`. All routes are prefixed `/v1`.
The route table lives in `src/api/endpoints.ts`.

## How the client treats responses

Every response is parsed with `schema.safeParse()`. A mismatch throws `ContractViolationError`
naming the path and the failing fields — the request is treated as failed, not partially
rendered. So a response that is _almost_ right is not "mostly working"; it is an error.

Errors should use this envelope (`ApiErrorSchema`):

```json
{
  "code": "BAD_REQUEST | UNAUTHORIZED | NOT_FOUND | RATE_LIMITED | UPSTREAM_UNAVAILABLE | INTERNAL",
  "messageKey": "errors.generic",
  "message": "Human-readable, English, for logs",
  "details": {},
  "requestId": "optional, for tracing"
}
```

`messageKey` maps to an i18n key so the app can show the message in the user's language.

## Shared primitives

- **`LanguageCode`** — `en | hi | mr | bn | ta | te`. Adding one means updating
  `LanguageCodeSchema` on both sides.
- **Money** — integer rupees. No paise, no floats, no strings.
- **`LocalizedText`** — `{ "en": "...", "hi": "..." }`. **`en` is mandatory** and is the
  guaranteed fallback everywhere.
- **`Citation`** — `{ id, title, locator?, url?, snippet?, confidence? }`. Anything the RAG
  pipeline produces should carry these. An answer with no citations renders as unverified.

---

## `GET /v1/health`

Connectivity probe. Build this first — if it parses, the base URL, TLS, routing and the `/v1`
prefix are all correct, which removes four possible causes before anyone debugs a real
endpoint.

**Response** (`HealthResponseSchema`)

```json
{ "status": "ok", "version": "2026.09.08-a1b2c3d", "time": "2026-09-08T09:14:00Z" }
```

`status` is `ok | degraded`. `version` and `time` are optional but worth sending: `version`
matches a client bug report to a deploy, and `time` exposes clock skew.

Client: `checkHealth()` in `src/api/services/health.service.ts`. In mock mode it answers
locally, so the call is safe from either configuration.

---

## `GET /v1/schemes`

Returns the scheme catalogue.

```jsonc
{
  "items": [/* Scheme[] */],
  "dataDisclaimer": { "en": "...", "hi": "..." }, // optional; shows a banner when present
}
```

Key `Scheme` fields (full schema in `src/api/contracts/scheme.ts`):

| Field                                                           | Notes                                                                                                                     |
| --------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| `id`, `code`                                                    | `code` is the display identifier, e.g. `NSFDC-TL`                                                                         |
| `name`, `shortDescription`                                      | `LocalizedText`                                                                                                           |
| `category`                                                      | `MICRO_FINANCE`, `TERM_LOAN`, `EDUCATION_LOAN`, `WOMEN_SPECIFIC`, `ARTISAN`, `AGRICULTURE`, `GREEN_MOBILITY`              |
| `minLoanAmount`, `maxLoanAmount`                                | integer rupees                                                                                                            |
| `fundingSharePct`                                               | 0–1. `0.9` = 90% of project cost                                                                                          |
| `interestRateMinPct`, `interestRateMaxPct`                      | e.g. `6.5`                                                                                                                |
| `womenInterestRatePct`                                          | optional; used automatically when the applicant is female                                                                 |
| `maxTenureMonths`, `moratoriumMinMonths`, `moratoriumMaxMonths` |                                                                                                                           |
| `maxAnnualFamilyIncome`                                         | the ₹5,00,000 ceiling                                                                                                     |
| `channelPartnerTypes`                                           | which partner types may process it                                                                                        |
| `verified`                                                      | **false → the UI shows an "unverified data" warning.** Only set true per scheme once confirmed against a current circular |

`GET /v1/schemes/{id}` returns a bare `Scheme`.

---

## `POST /v1/recommendations`

The Smart Scheme Recommender. **The highest-value endpoint for the AI teammate.**

Request:

```jsonc
{
  "profile": {
    "projectType": "RETAIL_SHOP", // enum, see contracts/recommendation.ts
    "estimatedProjectCost": 200000,
    "annualFamilyIncome": 150000,
    "educationStatus": "SECONDARY",
    "gender": "FEMALE", // optional
    "age": 32, // optional
    "isUrban": false, // optional
    "stateCode": "MH", // optional
    "narrative": "free text in any language", // optional — for the RAG layer
  },
  "language": "hi",
  "limit": 5,
}
```

Response:

```jsonc
{
  "recommendations": [
    {
      "scheme": {/* full Scheme */},
      "score": 87, // 0–100, sorted desc by the server
      "eligibleLoanAmount": 180000, // what THIS applicant would get
      "applicableInterestRatePct": 5, // may be the women's rate
      "suggestedTenureMonths": 48,
      "suggestedMoratoriumMonths": 3,
      "reasons": [
        // rendered as "Why this scheme?"
        { "kind": "MATCH", "text": { "en": "...", "hi": "..." } },
        { "kind": "INFO", "text": { "en": "...", "hi": "..." } },
      ],
      "citations": [/* Citation[] */],
      "source": "AI", // RULE_ENGINE | AI | HYBRID
    },
  ],
  "nearMisses": [/* same shape, with kind:"MISMATCH" reasons explaining exclusion */],
  "generatedAt": "2026-09-07T10:00:00Z",
  "offline": false,
}
```

Notes for the implementer:

- **`reasons` is not optional in spirit.** Financial literacy is the stated problem; a
  recommendation that cannot explain itself has failed the brief. The app renders these
  prominently.
- **`nearMisses` matters.** Showing _why_ someone was excluded is often more useful than the
  match list — especially the income ceiling.
- The client already computes all of this offline via
  `src/features/recommender/ruleEngine.ts`. Reading that file tells you exactly what a
  reasonable baseline looks like; ideally the backend returns `HYBRID` — these rules for
  eligibility, RAG for the explanation and citations.

---

## `POST /v1/partners/search`

Geo-spatial Channel Partner locator.

Request:

```jsonc
{
  "location": { "latitude": 18.52, "longitude": 73.85 }, // optional
  "pincode": "411001", // optional
  "radiusKm": 25,
  "schemeId": "nsfdc-term-loan", // optional
  "schemeCategory": "TERM_LOAN", // optional
  "partnerTypes": ["SCA", "PSB"], // optional
  "onlyAccepting": true, // DEFAULT true — see below
  "language": "mr",
}
```

Response:

```jsonc
{
  "items": [
    {
      "id": "sca-mh-001",
      "name": "…",
      "localizedNames": { "hi": "…" }, // optional
      "type": "SCA", // SCA | PSB | RRB | NBFC_MFI
      "address": "…",
      "district": "…",
      "stateCode": "MH",
      "pincode": "411001",
      "location": { "latitude": 18.52, "longitude": 73.85 },
      "phone": "+91…",
      "supportedSchemeCategories": ["TERM_LOAN", "EDUCATION_LOAN"],
      "supportedSchemeIds": [],
      "eligibility": {
        "status": "ACCEPTING", // ACCEPTING | LIMITED | NOT_ACCEPTING
        "reasonKey": "partners.eligibility.healthy",
        "npaPct": 4.2,
        "overdueAmount": 1250000,
        "unutilisedLimit": 48000000,
        "lastAssessedAt": "2026-09-01T00:00:00Z",
      },
      "distanceKm": 2.4, // server-computed
      "languagesSpoken": ["mr", "hi", "en"],
      "lastUpdatedAt": "2026-09-01T00:00:00Z",
    },
  ],
  "fallbackUsed": false,
  "searchedFrom": { "latitude": 18.52, "longitude": 73.85 },
  "radiusKm": 25,
}
```

**The routing rule this endpoint exists to enforce:** never surface a partner that cannot
disburse. `eligibility.status` is computed server-side from NPA percentage, overdue amount and
unutilised limit — the client renders it and never re-derives it.

When `onlyAccepting: true` filters everything out, return the unfiltered list with
`fallbackUsed: true`. The app then shows them with an explicit warning rather than a dead end,
so the user can at least call ahead.

`reasonKey` must be one of the i18n keys under `partners.eligibility.*`
(`healthy`, `limitedFunds`, `highNpa`, `unknown`), or the app falls back to `unknown`.

`GET /v1/partners/{id}` returns a bare `ChannelPartner`.

---

## `POST /v1/assistant/query`

The multilingual RAG assistant.

Request:

```jsonc
{
  "query": "मुझे दुकान के लिए कितना ऋण मिल सकता है?",
  "responseLanguage": "hi",
  "history": [{ "role": "user", "content": "…" }], // last ~10 turns
  "profileContext": {
    // optional
    "annualFamilyIncome": 150000,
    "projectType": "RETAIL_SHOP",
    "stateCode": "MH",
  },
  "sessionId": "optional",
}
```

Response:

```jsonc
{
  "messageId": "msg_123",
  "answer": "…in the requested language…",
  "answerLanguage": "hi",
  "detectedQueryLanguage": "hi",
  "citations": [/* Citation[] */],
  "suggestedActions": [
    { "type": "OPEN_CALCULATOR", "label": "…", "principal": 200000, "annualRatePct": 6.5 },
    { "type": "START_RECOMMENDER", "label": "…" },
    { "type": "OPEN_SCHEME", "schemeId": "nsfdc-mcf", "label": "…" },
  ],
  "followUpQuestions": ["…", "…"],
  "grounded": true,
  "sessionId": "sess_abc",
}
```

- **Answer in `responseLanguage`.** The user picked it; a query typed in Hindi with the UI in
  Tamil should come back in Tamil.
- **`grounded: false`** makes the app show "I'm not fully sure — please confirm with a Channel
  Partner". Use it honestly; it is better than a confident wrong answer about someone's loan.
- `suggestedActions` render as tappable chips and are how the assistant hands users back into
  the app. `label` should be in the response language.

### Streaming (v1)

`AssistantStreamChunkSchema` defines the chunk shape so both sides can agree on it now. The
client does **not** implement SSE yet — that is a v1 task:
`{type:'token'|'citations'|'actions'|'done'|'error'}` over SSE at
`POST /v1/assistant/stream`. Not required for v0.

### `POST /v1/assistant/transcribe` (not yet used)

Speech-to-text for voice queries. Reserved in the route table; the client has no voice input
yet (ADR-010).

---

## Changing this contract

`src/api/contracts/` is shared between two people building in parallel.

- Adding an **optional** field is safe.
- Adding a **required** field is breaking — both sides ship together, or add it optional first
  and tighten later.
- Renaming needs three steps: add new as optional, migrate both sides, remove old.

Full checklist: `.agents/skills/api-contract-change/SKILL.md`.
