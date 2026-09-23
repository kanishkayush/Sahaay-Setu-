# field-add

**An optional field ships independently. A required field is a breaking change that must land
on both sides together.**

## Why it matters

`apiRequest()` runs `schema.safeParse()` on every response and throws if it fails. There is no
partial success. So adding a required field to a response schema means: from that commit until
the backend deploys, **every** call to that endpoint fails — not just for the new field, for
the whole screen.

## Wrong

```ts
// src/api/contracts/scheme.ts
export const SchemeSchema = z.object({
  // …
  processingFeePct: z.number(), // ← required, backend doesn't send it yet
});
```

Result: every scheme response is rejected. The catalogue, the recommender and the detail screen
all break at once, with an error that looks like a client bug.

## Right

```ts
export const SchemeSchema = z.object({
  // …
  /** Optional until the backend ships it — see docs/API_CONTRACT.md. */
  processingFeePct: z.number().min(0).max(100).optional(),
});
```

Then handle absence explicitly at the render site:

```tsx
{
  scheme.processingFeePct !== undefined ? (
    <Row label={t('schemes.processingFee')} value={formatPercent(scheme.processingFeePct)} />
  ) : null;
}
```

## Tightening later

Once the backend reliably sends it:

1. Confirm it is present in every environment, not just staging
2. Drop `.optional()`
3. Remove the `undefined` branches
4. `npm run typecheck` — every site that assumed absence surfaces

## Defaults

`.default()` is a middle path: the field stays absent-tolerant but consumers see a value.

```ts
citations: z.array(CitationSchema).default([]),   // consumers can always .map()
```

Use it where a sensible empty value exists. Do **not** use it to paper over a missing figure —
`interestRatePct: z.number().default(0)` would render a 0% loan, which is worse than failing.

## Notes

- Add the mock field too, or the mock and the real backend diverge — see `mock-parity.md`.
- Update `docs/API_CONTRACT.md` in the same commit.
- Request schemas are the mirror image: adding a required field to a _request_ is safe for the
  client and breaking for the server. Same rule, other direction.
