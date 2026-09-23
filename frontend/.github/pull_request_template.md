## What this changes

<!-- One or two sentences. What does a user or teammate get that they didn't have before? -->

## Why

<!-- Link the requirement (R1–R4 in context/problem-statement.json), the issue, or the reason. -->

## Checks

- [ ] `npm run verify` passes (typecheck + lint + i18n)
- [ ] `npx expo export --platform android` succeeds — **required** if this touches imports,
      navigation or native modules
- [ ] Tested on a device or emulator

## Project rules

- [ ] No hardcoded user-visible strings — everything goes through `t()`
- [ ] No hardcoded colours or spacing — everything from `@/theme`
- [ ] Data flow respected: `screen → hook → service`; no `fetch` or `src/api/mock/` in a screen
- [ ] Touch targets ≥ 48dp, body text ≥ 16px, status not signalled by colour alone
- [ ] Any new endpoint has a mock in `src/api/mock/server.ts`

## If this touches the API contract

- [ ] `docs/API_CONTRACT.md` updated in this PR
- [ ] Backend teammate told what changed
- [ ] New required fields ship on both sides together (or were added optional first)

## Context files

- [ ] `context/state.json` updated if this completes something meaningful
- [ ] ADR added to `context/decisions.json` if this makes an architectural choice

## Screenshots

<!-- For UI changes. Ideally in two languages — English and one Indic script — so script
     rendering and overflow are visible. -->
