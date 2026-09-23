# field-rename

**Never rename in one commit. Add the new name as optional, migrate both sides, then remove the
old one.**

## Why it matters

A one-step rename breaks whichever side deploys second, and both sides cannot deploy
simultaneously across two repos. The three-step migration means neither side is ever broken —
there is simply a window where both names are accepted.

## Wrong

```ts
// one commit
export const ChannelPartnerSchema = z.object({
  distanceMetres: z.number(), // was: distanceKm
});
```

The client now rejects every partner response until the backend ships the matching change, and
the backend breaks every other consumer the moment it does.

## Right

### Step 1 — accept both, prefer the new

```ts
export const ChannelPartnerSchema = z.object({
  /** @deprecated use distanceMetres — removal tracked in context/state.json */
  distanceKm: z.number().nonnegative().optional(),
  distanceMetres: z.number().nonnegative().optional(),
});
```

Read through one helper so the fallback lives in exactly one place:

```ts
export function partnerDistanceKm(p: ChannelPartner): number | undefined {
  if (p.distanceMetres !== undefined) return p.distanceMetres / 1000;
  return p.distanceKm;
}
```

### Step 2 — backend ships the new name

Both are accepted; the helper silently starts using the new one. Nothing breaks.

### Step 3 — remove the old

Once the backend no longer sends `distanceKm` in any environment: delete the field, delete the
fallback branch, `npm run typecheck`.

## Real example

The seed data models `distanceKm`. If the backend returns metres — a genuinely easy mismatch
to ship — this migration is the safe path, and the unit belongs in the field name precisely so
the mismatch is visible in review rather than in production.

## Notes

- Removing a field follows the same shape: make it `.optional()`, stop reading it, then delete.
- Track the in-flight migration in `context/state.json → next` so a fresh session knows both
  names are temporary.
- Do not skip step 1 because "we'll deploy together". Across two repos, you will not.
