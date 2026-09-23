# Contributing

## Setup

```bash
npm install
npm start
```

Requires Node 20+. No backend needed — the app runs on a bundled mock.

## Before you push

```bash
npm run verify
```

Runs typecheck, lint and i18n coverage. If you touched imports, navigation or anything
native, also run a real bundle — it is the only thing that catches a broken module graph:

```bash
npx expo export --platform android
```

## The rules that matter

**Data flow is one-directional.** `screen → hook → service → mock or HTTP`. A screen never
imports `src/api/mock/` and never calls `fetch`. If you need data the service layer does not
expose, add a function to the service.

**Mock every new endpoint.** `src/api/mock/server.ts` must stay complete, or you break the
"runs with no backend" property the whole team relies on.

**No hardcoded user-visible strings.** Add the key to `src/i18n/locales/en.json`, use `t()`.

**No hardcoded colours or spacing.** Everything from `@/theme`.

**Use `Text` from `@/components/ui`**, never react-native's — ours carries the line heights
Indic scripts need.

**Accessibility is not optional here.** Touch targets ≥ 48dp, body text ≥ 16px, status never
signalled by colour alone. Our users are often first-time smartphone owners on cheap devices
outdoors.

**Do not un-label prototype data.** Unverified schemes keep `verified: false` and their UI
warnings. Real people would be making real financial decisions on this.

## Changing the API contract

`src/api/contracts/` is shared with the backend teammate — changing it is a cross-team change.
Read `.agents/skills/api-contract-change/SKILL.md` first. Short version: optional fields are
safe, required fields are breaking, renames take three steps.

## Adding a language

`.agents/skills/add-a-language/SKILL.md`. About fifteen minutes; partial translations are fine
because English is always the fallback.

## Commits

Conventional-ish prefixes: `feat:`, `fix:`, `docs:`, `refactor:`, `chore:`.

If an AI assistant wrote the change, say so in a `Co-Authored-By:` trailer. The history should
be honest about who wrote what.

## Keep the project memory current

If an AI assistant is doing the work, it should checkpoint as it goes:

```bash
bash .agents/checkpoint.sh save --agent claude-code --task "..." \
  --verified "fact=the command that proves it" --next "..."
```

Whoever does the work — human or agent — when something meaningful lands, update
`context/state.json`: move it into `done`, add a `verified` entry with the command output that
proves it, adjust `next`. Made an architectural choice? Append an ADR to
`context/decisions.json`.

Those files are how the next person, or the next AI session, picks up without re-deriving
everything. `.agents/PROTOCOL.md` has the full protocol.
