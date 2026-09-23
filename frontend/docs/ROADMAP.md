# Roadmap

Live status lives in `context/state.json`. This is the wider view.

## v0 — done

The full frontend, running on a bundled mock backend, demoable with no server and no internet.

- Six-language UI with device detection, persistence and English fallback
- Smart Scheme Recommender — 5-step wizard, results with explanations and near-misses
- Deterministic on-device rule engine (offline fallback + explainability baseline)
- EMI calculator with moratorium handling and full amortisation schedule
- Partner locator with fund-health filtering, map and list
- Multilingual assistant chat with citations, suggested actions and text-to-speech
- **Voice input and output** — a dedicated voice screen and a mic in the chat composer,
  both on one pipeline, with speech-to-text capability-detected rather than assumed
- Partner prudential norms encoded per partner type, cited from archived NSFDC pages
- Typed API contract with runtime validation
- Design system and accessibility floor

Verified: production bundle builds, typecheck, lint and format clean, i18n 100% across all six
locales, EMI math matches textbook values, rule engine behaves correctly across five applicant
personas, and the voice pipeline runs end to end from the text-query stage. The microphone
itself is the one thing still unverified — device capture is blocked in the preview browser,
so it needs a human to speak into it once.

## v1 — backend integration

The critical path. Roughly in order:

1. Wire the real API (`EXPO_PUBLIC_USE_MOCK_API=false`) endpoint by endpoint
2. **Finish verifying the scheme catalogue.** Five of eight are done and cited; Mahila
   Samriddhi, Laghu Vyavsay and Green Business still need their figures from an official
   NSFDC page. Also settle whether Mahila Kisan and Shilpi Samridhi are closed — sources
   conflict, so both are currently removed.
3. **Get the partner master and a fund-health feed from NSFDC.** Agency names are verified but
   the directory holds five of 37 SCAs, and per-partner figures are not published anywhere
   public. The norms are known and now encoded per partner type in
   `src/features/partners/eligibilityNorms.ts`; the data is not. `requiredInputsFor()` derives
   the exact field list to ask NSFDC for. This is the one item the app cannot solve on its own.
4. AI-grounded recommendations with citations (`source: 'HYBRID'`)
5. **Native-speaker review of mr, bn, ta and te.** All four are complete but AI-translated;
   each records `reviewStatus` in its `_meta`. Start from `TRANSLATION_GLOSSARY.md`.
6. Test suite — start with `emi.ts` and `ruleEngine.ts`, both already pure and both currently
   verified by throwaway scripts that should become real tests

Items 2, 3 and 5 are what turn this from a convincing prototype into something that could be
put in front of a real beneficiary.

## v2 — depth

- **Voice input on native.** Shipped on web via the Web Speech API (ADR-019); native still
  needs either a dev build with an STT config plugin or the backend's
  `POST /v1/assistant/transcribe`. `detectProvider()` will claim the backend provider the day
  that endpoint exists — until then the mic is absent on native rather than fake (ADR-010).
- **Streaming AI responses.** The contract and client already support SSE.
- **Offline scheme catalogue** bundled and refreshed in the background.
- **Document checklist** with progress tracking per scheme.
- **Application status tracking**, if Channel Partners can expose it.
- **Deep links / QR** so a field worker can hand someone a pre-filled recommendation.
- Dark mode. (The vector icon set that used to sit here shipped — see ADR-014.)

## Deliberately out of scope

- **In-app loan applications.** Applications happen at the Channel Partner. Building a form
  here would collect Aadhaar and certificate numbers from a vulnerable population for no
  benefit (ADR-011).
- **Accounts and login.** v0 is anonymous by design. Nothing needs identity.
- **Storing user profiles server-side.** The profile lives on the device and is sent only as a
  request body.

## Open questions

Tracked in `context/state.json → openQuestions`:

- Which languages beyond these six does the jury expect?
- Does the backend serve the scheme catalogue, or does it stay bundled for offline use?
- Is there a real data source for per-partner NPA and fund utilisation?
