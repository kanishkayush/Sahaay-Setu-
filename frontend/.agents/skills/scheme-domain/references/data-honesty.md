# data-honesty

**Every scheme figure here is unverified and every Channel Partner is invented. Both are
labelled in the data and surfaced in the UI. Do not remove the labels.**

## Why it matters

This is the failure mode that would matter most. People using this app are deciding whether to
take on debt. A screen that presents invented loan terms with the confidence of an official
source could send someone to the wrong branch, or into the wrong product, on the strength of a
number nobody checked.

Looking visibly honest about prototype data is strictly better than looking finished.

## What is actually unverified

**`src/api/mock/fixtures/schemes.ts`** — eight schemes. **Five are verified** against
`nsfdc.nic.in/scheme` (checked 2026-09-07) and carry citations with `verified: true`. **Three
carry `verified: false`** — they exist, but their current loan limits, rates, tenures and
moratoria could not be read from an official page, so the UI warns on them. Two further
schemes were removed outright because sources conflicted on whether they are still open.

**`src/api/mock/fixtures/partners.ts`** — five State Channelizing Agencies whose **names and
role are verified**. Coordinates are city-level, not the exact office. No partner carries a
phone number the organisation does not publish, and **none carries an NPA or fund-utilisation
figure at all** — those are not published per partner, so every record is `status: 'UNKNOWN'`.
The eligibility norms are encoded per partner type in
`src/features/partners/eligibilityNorms.ts`; they are not one threshold.

**`src/api/mock/fixtures/assistant.ts`** — keyword matching, not a model. Returns
`grounded: false` when it does not recognise a question.

## Wrong

```ts
verified: true,     // ← "it looks more polished in the demo"
```

```ts
// removing the header so the file reads cleaner
export const MOCK_SCHEMES: Scheme[] = [/* … */];
```

```ts
// flipping the whole catalogue at once after checking two schemes
MOCK_SCHEMES.forEach((s) => {
  s.verified = true;
});
```

## Right

Keep the flag false until that specific scheme is confirmed, then flip **that one**:

```ts
{
  id: 'nsfdc-mcf',
  // …
  citations: [{ id: 'nsfdc-circular-2026-01', title: 'NSFDC Circular 2026-27/03', locator: 'para 4.2' }],
  verified: true,                    // ← this scheme, individually confirmed
  lastUpdatedAt: '2026-09-15T00:00:00.000Z',
}
```

Verification is per-scheme because the figures come from different circulars and will be
confirmed at different times.

## What the flags drive

| Flag                        | UI                                              |
| --------------------------- | ----------------------------------------------- |
| `Scheme.verified === false` | warning chip on cards, banner on detail         |
| `dataDisclaimer`            | banner above the catalogue                      |
| `grounded === false`        | "confirm with a Channel Partner" caveat         |
| `offline === true`          | offline-result chip                             |
| `fallbackUsed`              | explanation of why unhealthy partners are shown |
| `USE_MOCK_API`              | prototype-data banner on Home and Profile       |

## Notes

- Fixture file headers are the warning for the next developer, the way the chips are the
  warning for the user. Keep both.
- Verification is owned by the backend/data teammate — `context/state.json → next` items N2
  and N3.
- ADR-009 records this decision.
- If a demo needs to look cleaner, verify the data. Do not hide the label.
