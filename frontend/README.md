# सहाय सेतु · Sahaay Setu

**Your bridge to the right loan.**

A multilingual mobile app that helps Scheduled Caste entrepreneurs and students find the
concessional credit scheme meant for them, understand exactly what they will repay, and reach
a Channel Partner who can actually process the application.

> **Smart India Hackathon · Problem Statement 26092**
> AI-Driven Scheme Matching for Marginalized Entrepreneurs
> Ministry of Social Justice and Empowerment (MoSJE)

---

## The problem

Concessional loans exist — NSFDC funds up to 90% of a project at rates starting around 6.5% a
year, for families earning under ₹5 lakh. But you cannot apply for them directly. Funds route
through a Channel Finance System of 37 State Channelizing Agencies and 55 further Channelizing
Agencies: state corporations, public sector banks, regional rural banks and NBFC-MFIs.

Two things go wrong. People do not know which scheme fits their situation — Micro Finance up to
a ₹1.40 lakh unit cost? A Term Loan up to ₹50 lakh? An education loan? And they cannot tell
which nearby partner is authorised for their category and actually able to disburse right now.

The result is misrouted applications and delayed disbursements, for the people who can least
afford the delay.

### This is measured, not assumed

From the Ministry's own [evaluation of NSFDC](https://socialjustice.gov.in/public/ckeditor/upload/Summary%20Report-Evaluation%20of%20NSFDC_1648795113.pdf)
(Centre for Market Research and Social Development, 2020):

| Finding                                                                                     | Why it shapes this app             |
| ------------------------------------------------------------------------------------------- | ---------------------------------- |
| **57.2%** applied at the gram panchayat office; only **15.9%** at the partner's head office | People don't know which counter    |
| **61.1%** heard about their scheme from friends; only **30.8%** from an official            | Discovery is word of mouth         |
| Partners took **1 month to 1 year** to deploy funds                                         | Why the app says "call ahead"      |
| **93.4%** who struggled cited collateral; **77.5%** cited repeated office visits            | Margin money up front; fewer trips |
| **15.3%** illiterate, **45%** middle school, **10.4%** matriculate or above                 | The accessibility floor, measured  |

Two caveats we keep attached to these numbers. The partner-level findings come from a sample
of **five** channel partners, not the network. And the study predates both the 01.10.2023 rate
revision and the 07.01.2026 income-ceiling change, so it is evidence about **behaviour and
process**, never about current scheme figures. Full set with source item numbers in
[`context/problem-statement.json`](context/problem-statement.json) → `fieldEvidence`.

One thing that report does **not** say: it is not evidence of widespread under-utilisation.
Four of the five sampled partners disbursed over 90% of funds received and the fifth disbursed
more than double — in aggregate, 11% more than NSFDC provided. Recorded as `E8` so nobody on
this project cites it the wrong way round.

## What this app does

**Finds your scheme.** Four plain questions — what you want to do, what it costs, your family
income, how far you studied — and you get ranked matches, each with a "Why this scheme?"
explanation. Schemes you narrowly missed show what blocked you, which is often more useful
than the match itself.

**Tells you what you'll repay.** A full EMI calculator that understands these products: 90%
funding shares, scheme loan ceilings, and the repayment holiday — including whether interest
during that holiday is added to your loan or paid monthly. Works with no internet.

**Routes you to a partner.** State Channelizing Agencies by location or PIN code, filtered by
fund health so you are not sent somewhere that cannot disburse. See
[Data honesty](#-data-honesty) for what is and is not known here.

**Speaks your language.** English, हिन्दी, मराठी, বাংলা, தமிழ், తెలుగు — all six complete —
including an assistant you can ask questions in your own language, with answers read aloud.

**Listens, too.** Press one button, ask out loud in your own language, and hear the answer
back — on the dedicated voice screen or from the mic in the chat composer. The answer is
always shown as text with its sources as well: a rupee figure you can only hear is one you
cannot check. Where speech is unavailable the app says why and offers typing; it never shows
a microphone that cannot listen.

---

## The voice pipeline

Both voice surfaces run the same stages, wired differently for their context:

```
VOICE UI → Speech-to-Text → "text query" → POST /v1/assistant/query
         → ChatResponse → Text-to-Speech
```

|                                            | Transcript                               | Spoken reply      |
| ------------------------------------------ | ---------------------------------------- | ----------------- |
| [**Ask by voice**](app/voice.tsx)          | sent immediately                         | always            |
| [**Ask Sahaay**](app/assistant.tsx) (chat) | fills the composer, editable before send | only if you spoke |

The difference is deliberate. A single spoken question shouldn't need a second tap to send. A
multi-turn conversation already has an edit field on screen, and a misheard question about a
loan is worth one tap to fix. Replies read themselves aloud only when the question was spoken
— someone who typed has a "Read aloud" button and doesn't need audio starting unbidden.

**Speech-to-text is capability-detected, never assumed.** The Web Speech API is real, free and
needs no backend, so the mic works today on web across all six languages via `-IN` locales.
`POST /v1/assistant/transcribe` is contracted for native but is deliberately not claimed until
it exists. Where no provider is available the mic is **absent, not dead** — the voice screen
explains why, the chat screen just falls back to typing.

That rule is [ADR-010](context/decisions.json), and it's enforced in
[`speechToText.ts`](src/features/voice/speechToText.ts) rather than trusted: a microphone that
does nothing teaches someone the app is broken, and these users are the least able to afford
giving up on it.

---

## Screens

16 screens across a five-tab shell.

|                    |                                                              |
| ------------------ | ------------------------------------------------------------ |
| **Language first** | The very first screen, every option in its own script        |
| **Home**           | What you can get, then the tools, then how it works          |
| **Find my scheme** | 5-step wizard, one question per screen, large touch targets  |
| **Results**        | Ranked matches, category filters, near-misses with reasons   |
| **Schemes**        | Full catalogue, filterable                                   |
| **EMI calculator** | Live figures and the complete repayment schedule             |
| **Partners**       | List and map, fund-health filtering, directions              |
| **Ask by voice**   | Speak the question, hear the answer, see it with citations   |
| **Ask Sahaay**     | Multilingual chat — same voice pipeline, mic in the composer |
| **Profile**        | Language, saved answers, saved schemes                       |

---

## Quick start

```bash
git clone https://github.com/parthp-4/sahaay-setu.git
cd sahaay-setu
npm install
npm start
```

Press `a` for Android, `i` for iOS, or scan the QR with **Expo Go**. Open `w` for the browser.

**No backend needed.** The app ships with a full mock backend and runs completely offline.

### Connecting a real backend

```bash
cp .env.example .env
```

```env
EXPO_PUBLIC_USE_MOCK_API=false
EXPO_PUBLIC_API_BASE_URL=https://your-api.example.com
```

That is the entire integration — see [`docs/BACKEND_HANDOFF.md`](docs/BACKEND_HANDOFF.md).

---

## Stack

TypeScript (strict) · React Native via **Expo SDK 57** · **expo-router** · **zustand** +
**React Query** · **i18next** · **Zod** (the API contract is Zod schemas, validated at runtime)

## Layout

```
app/               16 screens (expo-router — file path is the route)
src/
  api/
    contracts/     ⚠️ Zod schemas — the contract shared with the backend
    services/      the only door to data
    mock/          in-memory backend + fixtures
  features/
    calculator/    pure EMI math — no React, no network
    partners/      NSFDC prudential norms, encoded per partner type
    voice/         speech-to-text providers, TTS, speech locales
    recommender/   deterministic rule engine
  components/      ui/ (16, incl. a 29-icon SVG set) · domain/ (5)
  i18n/            6 locales × 319 keys
  theme/           design tokens
design/            mirrored design system (see below)
context/           machine-readable project state for AI agents
docs/              architecture, API contract, backend handoff, i18n, design, glossary, roadmap
.agents/           working protocol, checkpoint CLI, 4 skills
```

## Documentation

|                                                                |                                                                   |
| -------------------------------------------------------------- | ----------------------------------------------------------------- |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)                 | How the pieces fit, and why the mock backend ships inside the app |
| [`docs/API_CONTRACT.md`](docs/API_CONTRACT.md)                 | Every endpoint, request and response                              |
| [`docs/BACKEND_HANDOFF.md`](docs/BACKEND_HANDOFF.md)           | What the backend teammate owns, in suggested order                |
| [`docs/DESIGN_SYSTEM.md`](docs/DESIGN_SYSTEM.md)               | Tokens, components, and the accessibility floor                   |
| [`docs/I18N.md`](docs/I18N.md)                                 | How language selection and fallback work                          |
| [`docs/TRANSLATION_GLOSSARY.md`](docs/TRANSLATION_GLOSSARY.md) | Domain terms fixed across all six languages                       |
| [`docs/ROADMAP.md`](docs/ROADMAP.md)                           | What is done, what is next, what is out of scope                  |

## Commands

```bash
npm start                             # dev server
npm run verify                        # typecheck + lint + format + i18n coverage
npm run i18n:check                    # translation coverage per locale
npx expo export --platform android    # real production bundle
```

---

## ⚠️ Data honesty

This is the part to read before demoing.

### Schemes — 5 of 8 verified

Verified against [nsfdc.nic.in](https://nsfdc.nic.in/scheme) on 7 September 2026, each
carrying a citation in the code:

| Scheme            | Loan                 | Rate   | Term  | Moratorium                        |
| ----------------- | -------------------- | ------ | ----- | --------------------------------- |
| Micro Finance     | ₹1.25L (unit ₹1.40L) | 6.5%   | 3 yr  | 3 mo                              |
| Term Loan         | ₹45L (project ₹50L)  | 8%     | 7 yr  | 6 mo (12 plantation/construction) |
| Educational Loan  | ₹40L or 90% of fee   | 6.5%   | 12 yr | course + 1 yr                     |
| Aajeevika (AMY)   | ₹1.25L               | 15%    | 3 yr  | 3 mo                              |
| Udyam Nidhi (UNY) | ₹4.50L               | 13–15% | 5 yr  | 3 mo                              |

The ₹5 lakh income ceiling is confirmed twice — by NSFDC and by
[socialjustice.gov.in](https://socialjustice.gov.in/schemes/34) — effective 07.01.2026.

**Three remain unverified** and are labelled as such in the app: Mahila Samriddhi Yojana,
Laghu Vyavsay Yojana, Green Business Scheme. NSFDC lists them; their figures could not be
retrieved from an official page.

**Two were removed.** Mahila Kisan Yojana and Shilpi Samridhi Yojana — sources conflict on
whether they closed in 2020. Recommending a discontinued scheme sends someone to a branch for
a product that may not exist.

**Only `nsfdc.nic.in` counts as verification** (ADR-016). Third-party aggregators contradict
NSFDC and each other, apparently quoting figures from before the 01.10.2023 revision.

### Partners — verified names, no fund data

The directory holds **five State Channelizing Agencies** whose names and role are confirmed
from state government and NSFDC sources: MPBCDC and LIDCOM (Maharashtra), DSFDC (Delhi),
TAHDCO (Tamil Nadu), and the West Bengal SC/ST/OBC Development & Finance Corporation. It is a
partial directory, not the full network.

**No partner carries a phone number unless the organisation publishes one**, and none carries
an NPA figure. NSFDC publishes the eligibility _norms_ but **not the per-partner figures**. So
every partner shows `UNKNOWN` fund status and the app tells you to call before you travel.

The norms are not one rule, and flattening them into one is how you get a number that looks
rigorous and is wrong. They are encoded per partner type in
[`eligibilityNorms.ts`](src/features/partners/eligibilityNorms.ts):

| Partner type | Its own condition                                                       |
| ------------ | ----------------------------------------------------------------------- |
| **SCA**      | State government or bank guarantee in place                             |
| **RRB**      | Net NPA below **15%** in ≥3 of the last 6 years; profit in ≥3 of 6      |
| **PSB**      | MoA in force; utilisation certificate filed; nothing overdue on the day |
| **NBFC-MFI** | Gross NPA below **2%**, net NPA below **0.5%**; mfr5 rating; 3y profit  |

Plus, for every type: nothing owed to NSFDC over a year old, and ≥80% cumulative utilisation.
An RRB may carry a net NPA of 15% and stay eligible while an NBFC-MFI must stay below 0.5% —
a thirtyfold spread inside one network.

The partner detail screen shows the norms for that partner's type and then names the exact
fields we would need to evaluate them. That is a real data dependency for the partner-routing
requirement, not a gap in the UI. It needs a feed from NSFDC.

> **Source caveat.** NSFDC restructured its site: `nsfdc.nic.in/scheme` resolves, but every
> `/en/*` path — including the pages these norms come from — now returns 404. Each norm was
> read **verbatim from a dated Wayback Machine capture** of the original NSFDC page
> (2024-10-04 to 2025-03-17), so these are real citations at permanent URLs, held at
> `confidence: 0.9`. Not 1.0, because the captures are a year or two old and the live pages are
> gone — a later revision would be invisible to us.

### The assistant

`src/api/mock/fixtures/assistant.ts` is keyword matching, not a model. It returns
`grounded: false` when it does not recognise a question, and the UI says so.

### Translations

All six languages are complete, but **mr, bn, ta and te are AI-translated and not yet
native-reviewed** — each locale records this in `_meta.reviewStatus`. These are financial terms
in front of people deciding whether to take on debt. Start from
[`docs/TRANSLATION_GLOSSARY.md`](docs/TRANSLATION_GLOSSARY.md).

---

## Accessibility is a constraint, not a polish pass

The users are often first-time smartphone owners, on low-cost Android devices, outdoors in
bright sun, making a financial decision. So:

- Touch targets never below **48dp**; body text never below **16px**, nothing below 13px
- Contrast at or above **WCAG AA** — semantic colours were darkened where the design system's
  own values failed (its `warn` was 1.92:1 on white)
- **Status is never signalled by colour alone** — always an icon and a label too
- **Indic-aware line heights.** Latin-tuned leading clips Devanagari matras and Tamil
  descenders. Tab labels wrap rather than truncate.
- **Steppers, not drag sliders** — a thin handle is hard on a cheap touchscreen and
  inaccessible to a screen reader

## Design

The visual language comes from an Open Design system, mirrored into
[`design/`](design/README.md) so it is versioned next to the code. Four of its values were
deliberately not adopted — sub-13px text, 1.47 line-height, the SF Pro font stack (no Indic
coverage), and the semantic colours failing AA. See ADR-014 and
[`docs/DESIGN_SYSTEM.md`](docs/DESIGN_SYSTEM.md).

---

## Working with AI assistants

Set up so any AI assistant can pick this up cold, with no prior conversation.

```bash
bash .agents/checkpoint.sh resume
```

**Chat history is not project state.** The repo carries its own memory in two layers:

| Layer             | Path                  | Changes       | Holds                        |
| ----------------- | --------------------- | ------------- | ---------------------------- |
| **Durable truth** | `context/*.json`      | slowly        | What the project _is_        |
| **Session state** | `.checkpoints/*.json` | every session | Where the last agent stopped |

`resume` prints the latest checkpoint, the actual git state, a **reconciliation verdict** (same
commit? uncommitted? diverged?), and the current `next` list — so an agent never resumes off a
record that no longer matches reality.

Every verified fact carries the command that proves it. `state.json` says
_"P=100000 @10%/12mo → EMI 8791.59 exact"_, not _"the calculator works"_.

**Four skills, 31 rules** in [`.agents/skills/`](.agents/skills/README.md) — `sahaay-frontend`,
`api-contract-change`, `scheme-domain`, `add-a-language`. Each rule is a wrong example, a right
example, and why it matters.

Entry points: [`CLAUDE.md`](CLAUDE.md) · [`AGENTS.md`](AGENTS.md) ·
[`.cursor/rules/`](.cursor/rules/) · **17 ADRs** in `context/decisions.json`

---

## Team

Frontend in this repository. Backend, multilingual AI and the RAG pipeline are built in
parallel — see [`docs/BACKEND_HANDOFF.md`](docs/BACKEND_HANDOFF.md) and
[`docs/API_CONTRACT.md`](docs/API_CONTRACT.md).

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md).

## Licence

MIT — see [`LICENSE`](LICENSE).
