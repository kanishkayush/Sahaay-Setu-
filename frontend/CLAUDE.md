# Sahaay Setu — Claude Code instructions

@.agents/PROTOCOL.md

## What this is

Frontend for **SIH Problem Statement 26092** (Ministry of Social Justice and Empowerment):
a multilingual mobile app that matches SC entrepreneurs and students to the right
concessional credit scheme and the nearest Channel Partner who can actually process it.

React Native (Expo SDK 57) + TypeScript. The backend and the multilingual AI/RAG pipeline are
built by a separate teammate in a separate repo.

---

## Checkpoint protocol

### On EVERY session start

```bash
bash .agents/checkpoint.sh resume
```

This prints the latest checkpoint, the actual git state, a reconciliation verdict, and the
current `next` list. Then:

1. **Reconcile** the checkpoint against real git state (PROTOCOL §5). Same commit and a clean
   tree means resume from `next_action`. Uncommitted changes mean someone edited files after
   the checkpoint — inspect them first. Diverged commits mean read the new commits before
   assuming anything.
2. **Announce in one line:** "Resuming from `{id}`. Last: `{task}`. Next: `{next_action}`."
   If there is no checkpoint, say it is a fresh start and bootstrap from `context/`.

### During work

Save a checkpoint after each completed step, after any successful build or verification, and
before anything destructive:

```bash
bash .agents/checkpoint.sh save --agent claude-code \
  --task "..." --done "step;step" \
  --verified "fact=the command you ran and what it printed" \
  --next "..." --next-file "path" --notes "..."
```

Or let the script run the checks and record the proof itself:

```bash
bash .agents/checkpoint.sh verify claude-code
```

### Before ENDING any session, or when context is getting long

1. Save a final checkpoint with an accurate `next_action` — always.
2. If a milestone actually landed, promote it into `context/state.json` (`done` / `next` /
   `verified`), and append an ADR to `context/decisions.json` if you made an architectural
   choice.

**Checkpoint every ~15 minutes. Update `context/` when a milestone lands.**

---

## Dual-AI awareness

Cursor may also be working in this repo.

- Check `.checkpoints/_latest.json` before starting — if `by` is `cursor`, read that
  checkpoint instead of re-deriving what happened.
- Always identify yourself as `claude-code` in the `agent` field and in `updatedBy`.
- If both tools are active, work in different directories and say which you have taken.
- End commit messages with a `Co-Authored-By:` trailer.

---

## The five things that matter most

1. **Data flow is one-directional.** `screen → hook → service → mock or HTTP`. A screen never
   imports `src/api/mock/` and never calls `fetch`.

2. **The mock backend is a feature, not scaffolding.** `USE_MOCK_API` defaults to true so the
   app is fully demoable with no server. Keep every new endpoint mocked.

3. **Nothing user-visible is hardcoded.** Strings go through `t()` into
   `src/i18n/locales/en.json`. Colours and spacing come from `@/theme`.

4. **Every figure is labelled with what is known about it.** Five of eight schemes are
   verified against `nsfdc.nic.in` and carry citations; three carry `verified: false` and the
   UI warns. Partner agency names are verified, but no partner carries an NPA or fund figure
   at all — NSFDC does not publish them, so every partner is `UNKNOWN`. Never upgrade a label
   to make a demo look cleaner, and never invent a figure to fill a field — real people would
   be making real financial decisions on this.

5. **Verify, then claim.** A fact without a proof is worthless to the next session. Record
   the command and its output, not "it works".

## Commands

```bash
npm start                             # Expo dev server
npm run verify                        # typecheck + lint + i18n coverage
npm run i18n:check                    # translation coverage per locale
npx expo export --platform android    # real bundle check

bash .agents/checkpoint.sh resume     # start of session
bash .agents/checkpoint.sh list       # checkpoint history
bash .agents/checkpoint.sh diff       # checkpoint vs actual git
```

## Skills

Load the matching skill before starting that kind of work:

| Skill                                 | Load before                               |
| ------------------------------------- | ----------------------------------------- |
| `.agents/skills/sahaay-frontend/`     | Any screen, component or hook             |
| `.agents/skills/api-contract-change/` | Anything under `src/api/`                 |
| `.agents/skills/scheme-domain/`       | Eligibility, EMI or partner-routing logic |
| `.agents/skills/add-a-language/`      | i18n work                                 |

Each `SKILL.md` is short by design and points at `references/` files — one rule each, with a
wrong example and a right one. Read the SKILL, then only the references you need.

## Project context

- `context/context.json` — what the project is, ownership split, conventions
- `context/state.json` — current milestone, done, next, verified facts
- `context/problem-statement.json` — the brief, mapped to code
- `context/domain.json` — channel-finance glossary and business rules
- `context/decisions.json` — ADR log; read before contradicting a past decision
