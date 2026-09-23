# Agent Protocol — Sahaay Setu

How any AI agent (Claude Code, Cursor, Copilot, Gemini, whatever comes next) works in this
repository. Read this once at the start of a session.

---

## 1. Chat history is not project state

If a session ends, crashes, or runs out of context, the next agent must **not** rebuild
context by re-reading a conversation. It loads a checkpoint, reconciles it against actual git
state, and resumes.

That means this repo carries its own memory, in two layers:

| Layer             | Path                  | Changes       | Holds                                                                                   |
| ----------------- | --------------------- | ------------- | --------------------------------------------------------------------------------------- |
| **Durable truth** | `context/*.json`      | slowly        | What the project _is_ — identity, ownership, domain rules, decisions, current milestone |
| **Session state** | `.checkpoints/*.json` | every session | What happened _this session_ — task, progress, verified facts, exactly what to do next  |

Neither replaces the other. `context/` answers "what am I working on"; `.checkpoints/` answers
"where did the last agent stop, and can I trust it".

## 2. Start every session with resume

```bash
bash .agents/checkpoint.sh resume
```

That single command prints the latest checkpoint, the actual git state, a reconciliation
verdict, and the current `next` list from `context/state.json`.

If it says **no checkpoint found**, bootstrap by reading in this order:

| Order | File                             | Gives you                                                   |
| ----- | -------------------------------- | ----------------------------------------------------------- |
| 1     | `context/context.json`           | What this project is, who owns what, where everything lives |
| 2     | `context/state.json`             | Where the build stands, and what is next                    |
| 3     | `context/problem-statement.json` | The brief and how each requirement maps to code             |
| 4     | `context/domain.json`            | Channel-finance vocabulary and business rules               |
| 5     | `context/decisions.json`         | Why things are as they are — check before contradicting one |

Then announce, in one line:

> Resuming from `{checkpoint id}`. Last: `{task}`. Next: `{next_action}`.

## 3. Checkpoint schema (v1)

```jsonc
{
  "schema_version": 1,
  "id": "chk_{timestamp}_{agent}_{hash}",
  "created_at": "ISO-8601",
  "agent": "claude-code | cursor | copilot | human",
  "project": "sahaay-setu",

  "task": {
    "description": "What you were working on",
    "plan": ["Step 1", "Step 2"],
    "status": "in_progress | blocked | completed",
  },

  "progress": {
    "completed": [{ "step": "...", "verified": true, "proof": "..." }],
    "in_progress": [{ "step": "...", "notes": "partial progress" }],
    "pending": [{ "step": "..." }],
  },

  "verified_facts": [
    {
      "fact": "...",
      "proof": "the command you ran and what it printed",
      "verified_at": "ISO-8601",
    },
  ],

  "workspace": {
    "git_branch": "main",
    "git_commit": "full SHA",
    "git_commit_message": "...",
    "files_changed": ["..."],
    "has_uncommitted": true,
    "diff_summary": "...",
  },

  "tool_results": [
    {
      "tool": "npm run verify",
      "result": "success | failure",
      "output_summary": "...",
      "at": "...",
    },
  ],

  "next_action": {
    "description": "Exactly what to do next",
    "target_file": "path/to/file.tsx",
    "context": "anything needed to execute it",
  },

  "context_notes": "Free-form notes for the next session",
}
```

**`verified_facts` is the part that matters most.** A fact without a proof is worthless to the
next agent — it just has to re-derive it. "The calculator works" is noise; "P=100000 @10% over
12 months → EMI 8791.59 exact" is something the next session can build on.

## 4. When to checkpoint

Save after:

- completing any plan step
- a successful build, bundle or verification run
- **before** any risky or destructive operation (a reset, a large refactor)
- switching tasks
- **ending a session — always**
- roughly every 15 minutes of active work, as a heartbeat

```bash
bash .agents/checkpoint.sh save --agent claude-code \
  --task "Wire the partner locator to the real backend" \
  --done "Swapped service to HTTP;Handled the fallbackUsed banner" \
  --verified "Bundle builds=npx expo export --platform android" \
  --next "Add retry on 429" --next-file src/api/client.ts \
  --notes "Backend returns distanceKm in metres, not km — flagged to the teammate."
```

`--verified` takes `fact=proof` pairs. Omit the proof and the script writes
`NO PROOF GIVEN` into the file, which is the point.

Checkpoints are committed to git. They are project history, not scratch files.

## 5. Reconciliation — trust, but check

A checkpoint records the git state it was written against. `resume` (and `checkpoint.sh diff`)
compares it to reality and tells you which case you are in:

| Verdict                              | What it means                                    | What to do                                                                                                           |
| ------------------------------------ | ------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------- |
| **Same commit, clean tree**          | Checkpoint is current                            | Resume from `next_action`                                                                                            |
| **Same commit, uncommitted changes** | Another agent or the human edited files after it | Inspect them. If they match an in-progress step, update it. If they conflict with `next_action`, flag it to the user |
| **Commits diverged (ahead)**         | Work was committed since                         | Read the new commits, mark those steps done, resume from the updated position                                        |
| **Diverged (behind or rewritten)**   | Something went wrong                             | Stop and flag it to the user before proceeding                                                                       |

Never resume blindly off a checkpoint that disagrees with git.

## 6. Promote durable results into `context/`

Checkpoints accumulate and get pruned. `context/` is what survives.

When something is genuinely finished, also update `context/state.json`:

- Finished a feature → add to `done`, remove the matching item from `next`
- Verified something → add to `verified` **with the proof**
- Learned something that changes the plan → update `next` or `openQuestions`
- Made an architectural choice → append an ADR to `context/decisions.json`

Set `updatedBy` to your agent name and `updatedAt` to today.

Rule of thumb: **checkpoint every 15 minutes, update `context/` when a milestone lands.**

## 7. Verify before you claim

```bash
npm run verify   # typecheck + lint + i18n coverage
```

For anything touching imports, navigation or native modules that is not enough — run a real
bundle, the only thing that catches a broken module graph:

```bash
npx expo export --platform android
```

Or let the script record the result for you:

```bash
bash .agents/checkpoint.sh verify claude-code
```

It runs `npm run verify`, saves a passing checkpoint with the proof attached, or saves a
`blocked` checkpoint and exits non-zero on failure. If a check fails, fix it or say plainly
that it fails. Never write "should work" into a checkpoint or into `state.json`.

## 8. More than one agent in this repo

Claude Code and Cursor (and a human) may all touch this repo.

1. **Read before write.** Check `.checkpoints/_latest.json` — if `by` is another agent, read
   their checkpoint rather than re-deriving what they did.
2. **Checkpoint on handoff.** Always save before ending a session, so the other tool can pick
   up.
3. **Identify yourself.** Set `agent` on every checkpoint and `updatedBy` in
   `context/state.json`. End commit messages with a `Co-Authored-By:` trailer naming the
   agent, so history shows who wrote what.
4. **Respect scope.** If a checkpoint marks work `in_progress`, do not overwrite those files
   without flagging it.
5. **No locks.** There is no locking scheme — the human running both tools is the arbiter.
   If two agents are active at once, work in different directories and say which you have
   taken.

## 9. Working rules

**Stay in your lane.** `context/context.json → ownership` says which surfaces belong to the
frontend and which to the backend teammate. The API contract in `src/api/contracts/` is
shared — changing it is a cross-team change, so flag it rather than doing it silently.

**Follow the data flow.** `screen → hook → service → mock or HTTP`. A screen must never
import from `src/api/mock/` or call `fetch` directly. If you want to, the service layer is
missing a function.

**No hardcoded user-visible strings.** Add the key to `src/i18n/locales/en.json` and use
`t('key')`.

**No hardcoded colours or spacing.** Everything comes from `@/theme`.

**Never dress up unverified data as real.** Fixtures carry their verification state in the
data: `verified: true` with citations where a figure was read from an official page,
`verified: false` with a UI warning where it was not, and `UNKNOWN` where the figure is not
published at all. Loud file headers say which is which. Do not upgrade a label to make a demo
look cleaner, and never invent a value to fill an empty field — see ADR-009 and ADR-016.

## 10. Project skills

`.agents/skills/` holds task-specific playbooks. Read the relevant one before starting that
kind of work rather than improvising:

| Skill                 | Use when                                                  |
| --------------------- | --------------------------------------------------------- |
| `sahaay-frontend`     | Writing or changing any screen, component or hook         |
| `api-contract-change` | Touching `src/api/` — contracts, services or the mock     |
| `scheme-domain`       | Eligibility, recommendation, EMI or partner-routing logic |
| `add-a-language`      | Adding a language or extending translations               |

Each is a `SKILL.md` in the Anthropic skill format, so Claude Code loads it directly and other
tools can read it as plain Markdown.

Each skill uses progressive disclosure: `SKILL.md` is short enough to read every time and
carries the rules you must not get wrong; `references/` holds one file per rule — a wrong
example, a right example, and why it matters — read only when that rule is in play. Do not
inline reference content back into `SKILL.md`.

`.agents/skills/README.md` explains how to add a rule or a new skill.

## 11. Command reference

```bash
bash .agents/checkpoint.sh resume              # start here, every session
bash .agents/checkpoint.sh save --agent … --task …
bash .agents/checkpoint.sh verify claude-code  # run checks, record the proof
bash .agents/checkpoint.sh list                # history
bash .agents/checkpoint.sh show --id <file>    # one checkpoint
bash .agents/checkpoint.sh diff                # checkpoint vs actual git
bash .agents/checkpoint.sh prune --keep 10     # trim old checkpoints
```
