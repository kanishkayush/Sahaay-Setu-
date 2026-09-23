# AGENTS.md — Sahaay Setu

Instructions for any AI coding agent working in this repository. Tool-agnostic: Claude Code,
Cursor, Codex, Gemini, Copilot and anything else read this file.

Claude Code users: `CLAUDE.md` is the entry point and imports `.agents/PROTOCOL.md`.
Cursor users: `.cursor/rules/` mirrors the same rules.

## Project

**Sahaay Setu** — multilingual mobile app for SIH PS 26092 (Ministry of Social Justice and
Empowerment). Matches Scheduled Caste entrepreneurs and students to the right concessional
credit scheme, works out what they will repay, and routes them to the nearest Channel Partner
able to process the application.

This repo is the **frontend only**. The backend and multilingual AI/RAG pipeline are built
separately. `context/context.json → ownership` records the split.

## Start here, every session

```bash
bash .agents/checkpoint.sh resume
```

Chat history is not project state. This repo carries its own memory in two layers, and that
one command reads both:

| Layer             | Path                  | Changes       | Holds                                             |
| ----------------- | --------------------- | ------------- | ------------------------------------------------- |
| **Durable truth** | `context/*.json`      | slowly        | What the project _is_                             |
| **Session state** | `.checkpoints/*.json` | every session | Where the last agent stopped, and what to do next |

`resume` prints the latest checkpoint, the actual git state, a reconciliation verdict, and the
current `next` list. Reconcile before acting — a checkpoint that disagrees with git is not
something to resume off blindly (PROTOCOL §5).

Then announce: _"Resuming from {id}. Last: {task}. Next: {next_action}."_

### If there is no checkpoint

Bootstrap from `context/`, in this order:

| File                             | Contents                                                         |
| -------------------------------- | ---------------------------------------------------------------- |
| `context/context.json`           | Master index: identity, stack, structure, ownership, conventions |
| `context/state.json`             | Current build state, verified facts with proofs, what's next     |
| `context/problem-statement.json` | The brief, with each requirement mapped to code                  |
| `context/domain.json`            | Channel-finance glossary and business rules                      |
| `context/decisions.json`         | ADR log — read before contradicting a past decision              |

Read `context.json` then `state.json` and you have the project. No conversation history needed.

## Checkpoint as you go

Save after each completed step, after any successful build, and before anything destructive:

```bash
bash .agents/checkpoint.sh save --agent <you> \
  --task "..." --done "step;step" \
  --verified "fact=the command you ran and what it printed" \
  --next "..." --next-file "path"
```

`--verified` takes `fact=proof` pairs. **A fact without a proof is worthless to the next
agent** — it just has to re-derive it. The script writes `NO PROOF GIVEN` if you omit one.

Always save before ending a session. When a milestone actually lands, promote it into
`context/state.json` as well — checkpoints get pruned, `context/` survives.

Checkpoint every ~15 minutes; update `context/` when a milestone lands.

## Stack

TypeScript (strict) · React Native via Expo SDK 57 · expo-router · zustand + React Query ·
i18next · Zod

## Rules

1. `screen → hook → service → mock or HTTP`. Never import `src/api/mock/` from a screen; never
   call `fetch` outside `src/api/client.ts`.
2. Use `@/` imports (resolved by Metro from tsconfig paths — there is deliberately no
   `babel.config.js`; see ADR-008).
3. Every user-visible string goes through `t()` into `src/i18n/locales/en.json`.
4. Every colour and spacing value comes from `@/theme`.
5. Use `Text` from `@/components/ui`, never react-native's — ours carries Indic line heights.
6. Touch targets ≥ 48dp, body text ≥ 16px, status never conveyed by colour alone.
7. Money is whole-rupee integers formatted through `@/utils/format` (lakh/crore grouping).
8. Unverified scheme data keeps `verified: false` and its UI warning.
9. `src/api/contracts/` is shared with the backend teammate — changing it is a cross-team
   change. See `.agents/skills/api-contract-change/SKILL.md`.

## Skills

Load the matching playbook before starting that kind of work rather than improvising:

| Skill                                                                | Load before                               |
| -------------------------------------------------------------------- | ----------------------------------------- |
| [`sahaay-frontend`](.agents/skills/sahaay-frontend/SKILL.md)         | Any screen, component or hook             |
| [`api-contract-change`](.agents/skills/api-contract-change/SKILL.md) | Anything under `src/api/`                 |
| [`scheme-domain`](.agents/skills/scheme-domain/SKILL.md)             | Eligibility, EMI or partner-routing logic |
| [`add-a-language`](.agents/skills/add-a-language/SKILL.md)           | i18n work                                 |

Each `SKILL.md` carries the rules you must not get wrong and points at `references/` — one file
per rule, with a wrong example and a right one. Read the SKILL, then only the references in
play.

## Verify before claiming

```bash
npm run verify                        # typecheck + lint + i18n coverage
npx expo export --platform android    # real production bundle
```

Or run the checks and record the proof in one step:

```bash
bash .agents/checkpoint.sh verify <you>
```

It saves a passing checkpoint with the proof attached, or a `blocked` one on failure. Then
record the durable result — and its proof — in `context/state.json`. Never write "should work"
into a checkpoint or into `state.json`.

## More than one agent here

Claude Code and Cursor may both touch this repo. Check `.checkpoints/_latest.json` before
starting — if `by` is another agent, read their checkpoint rather than re-deriving. Identify
yourself in the `agent` field and in `updatedBy`. If a checkpoint marks work `in_progress`, do
not overwrite those files without flagging it. There are no locks; the human is the arbiter.

## Data honesty

Mixed, and the distinction is the whole point.

**Schemes** — five of eight are verified against `nsfdc.nic.in/scheme` (checked 2026-09-07)
and carry citations; three carry `verified: false` and the UI warns on them. Two were removed
because sources conflicted on whether they are still open.

**Partners** — the five agency names and their SCA role are verified. No partner carries a
phone number the organisation does not publish, and none carries an NPA or fund-utilisation
figure at all: NSFDC publishes the eligibility norms but not the per-partner figures, so every
partner is `status: 'UNKNOWN'`. The norms themselves are encoded per partner type in
`src/features/partners/eligibilityNorms.ts`, each with the data field that would be needed to
evaluate it.

**Assistant** — `src/api/mock/fixtures/assistant.ts` is keyword matching, not a model.

Nothing here is invented; what is not known is marked as not known. Do not upgrade a label to
make a demo look cleaner. The warnings in the UI are deliberate.
