---
name: api-contract-change
description: "Use BEFORE touching anything in src/api/. Triggers: adding, renaming or removing a field in src/api/contracts/; adding an endpoint or route; changing a Zod schema; editing a service in src/api/services/; editing the mock in src/api/mock/; debugging a ContractViolationError or a response that renders as undefined; wiring the app to the real backend; anything described as 'the backend now returns…'. This directory is shared with a teammate building the backend in a separate repo — a careless edit here breaks their build, not just yours."
license: MIT
metadata:
  project: sahaay-setu
  version: '1.0.0'
  updated: 2026-09-07
  abstract: >
    How to change the Zod schemas that form the contract between this React Native client and
    a separately-built backend. Covers safe vs breaking field changes, the five-step endpoint
    checklist that keeps the mock at parity, rename migrations, and how to read a
    ContractViolationError.
---

# Changing the API contract

`src/api/contracts/` is the boundary between two people working in parallel in two repos.
Treat every change here as a cross-team change.

## What the contract is

Zod schemas doing three jobs at once:

1. **TypeScript types** for the app, via `z.infer`
2. **Runtime validation** — `apiRequest()` parses every response, so backend drift fails loudly
   at the network boundary instead of rendering `undefined` three screens deep
3. **The documentation itself** — `docs/API_CONTRACT.md` is prose around these files; when the
   two disagree, the schemas win

ADR-002 records why this is Zod rather than plain interfaces.

## Core principles

**1. Optional is safe, required is breaking.**
Adding `.optional()` ships independently. Adding a required field means the client rejects
every response until the backend sends it. Prefer optional-then-tighten.
→ `references/field-add.md`

**2. The mock must stay at parity.**
Every endpoint has a mock implementation. This is what keeps the frontend unblocked and the app
demoable with no server. An endpoint without a mock breaks a property the whole team relies on.
→ `references/mock-parity.md`

**3. Never rename in one step.**
Add the new name as optional, migrate both sides, then remove the old one. Three commits, not
one. → `references/field-rename.md`

**4. A ContractViolationError is a contract bug, not a client bug.**
It names the exact failing fields. Read it before changing anything.
→ `references/validation-failures.md`

**5. Tell the other side.**
Update `docs/API_CONTRACT.md` in the same commit, and tell the backend teammate what changed.
A schema change nobody announced is how integration day goes wrong.

## When to apply

Before editing anything under `src/api/`, and before answering "the backend now returns X, can
you handle it?"

## Rules

| Prefix        | Rule                                          | Read when                                |
| ------------- | --------------------------------------------- | ---------------------------------------- |
| `field-`      | [add](references/field-add.md)                | Adding a field to an existing schema     |
| `field-`      | [rename](references/field-rename.md)          | Renaming or removing a field             |
| `endpoint-`   | [add](references/endpoint-add.md)             | Adding a route — the five-step checklist |
| `mock-`       | [parity](references/mock-parity.md)           | Any change that touches `src/api/mock/`  |
| `validation-` | [failures](references/validation-failures.md) | Debugging a rejected response            |

## Things the contract deliberately encodes

Do not relax these without an ADR:

- **`LocalizedText` requires `en`.** English is the guaranteed fallback everywhere.
- **RAG output carries `citations`.** An answer with none renders as unverified.
- **`Scheme.verified`** gates the unverified-data warning in the UI.
- **`PartnerEligibility.status`** is computed server-side, against the norms for the partner's
  **type** — they differ per type and must never be collapsed into one threshold. The client
  renders the status and never re-derives it. `UNKNOWN` is a real state, not a placeholder.
- **Money is integer rupees.** No floats, no strings, no paise.

## After any change here

```bash
npm run typecheck   # every consumer of the changed type surfaces immediately
npm run verify
```

Then update `docs/API_CONTRACT.md`, and checkpoint what you changed so the other agent — and
the backend teammate — can see it.
