# rule-partner-routing

**Never surface a Channel Partner that cannot disburse. Fund health is judged server-side; the
client renders `eligibility.status` and never re-derives it.**

## Why it matters

This is requirement R3 in one sentence: _"ensuring applications aren't sent to partners with
high NPAs or overdues."_ A partner carrying 14.8% NPAs with zero unutilised limit will take an
application and sit on it. For someone who travelled to that branch and lost a day's earnings,
that is a worse outcome than being told to go somewhere else.

Two partners can be equally near and equally authorised, and only one can actually help.

## Wrong

```ts
// distance only
partners.sort((a, b) => a.distanceKm - b.distanceKm);
```

```ts
// client re-deriving the judgement — and against a threshold that does not exist
const canApply = partner.eligibility.npaPct < 10; // ← wrong twice over, see below
```

```ts
// hiding everything and showing an empty screen
const items = partners.filter((p) => p.eligibility.status === 'ACCEPTING');
return { items }; // ← dead end when the answer is "none nearby"
```

## Right

```ts
const accepting = items.filter((p) => p.eligibility.status !== 'NOT_ACCEPTING');
const useFallback = req.onlyAccepting && accepting.length === 0 && items.length > 0;

return {
  items: req.onlyAccepting && !useFallback ? accepting : items,
  fallbackUsed: useFallback,
  searchedFrom: origin,
  radiusKm: req.radiusKm,
};
```

`fallbackUsed` drives an explicit warning rather than an empty state:

> _"Every partner nearby is currently unable to take new applications. Showing them anyway so
> you can call ahead."_

Filtered-to-nothing is a real answer, but it must be an explained one.

## There is no single NPA threshold

This is the mistake most likely to be made here, and it was made once already. NSFDC's norms
are **partner-type-specific**:

| Type       | Its own condition                                                       |
| ---------- | ----------------------------------------------------------------------- |
| `SCA`      | State government or bank guarantee in place                             |
| `RRB`      | Net NPA below **15%** in ≥3 of the last 6 years; profit in ≥3 of 6      |
| `PSB`      | MoA in force; utilisation certificate filed; nothing overdue on the day |
| `NBFC_MFI` | Gross NPA below **2%**, net NPA below **0.5%**; mfr5 rating; 3y profit  |

Plus, for all four: nothing owed to NSFDC over a year old, and ≥80% cumulative utilisation.

An RRB may carry a net NPA of 15% and remain eligible while an NBFC-MFI must stay below 0.5%.
A single `npaPct < 10` check is wrong for three of the four types — and 10% is not even the
general RRB rule, it is the tighter Stand-up India one.

The encoded norms live in `src/features/partners/eligibilityNorms.ts`. Add to that file rather
than writing a threshold into a component.

## The four statuses

| Status          | Meaning                             | UI                                  |
| --------------- | ----------------------------------- | ----------------------------------- |
| `ACCEPTING`     | healthy fund position, low overdues | green, `✓`                          |
| `LIMITED`       | most funds already committed        | amber, `!` — shown, with the caveat |
| `NOT_ACCEPTING` | fails a norm for its type           | red, `✕` — hidden by default        |
| `UNKNOWN`       | **figures not published** — today's | neutral, `i` — shown, "call ahead"  |

`UNKNOWN` is the honest default and currently the only status any real partner carries. It is
not a placeholder to be filled in with a guess.

`onlyAccepting` defaults to **true** in `PartnerSearchRequestSchema`. That default is the
feature — and it deliberately does **not** hide `UNKNOWN`, because we cannot assert that an
unassessed partner is unavailable either.

## Authorisation is a separate filter

Fund health is necessary, not sufficient. A partner must also be authorised for the scheme:

```ts
if (req.schemeCategory) {
  items = items.filter((p) => p.supportedSchemeCategories.includes(req.schemeCategory));
}
if (req.schemeId) {
  items = items.filter(
    (p) => p.supportedSchemeIds.length === 0 || p.supportedSchemeIds.includes(req.schemeId),
  );
}
```

An empty `supportedSchemeIds` means "all schemes in the supported categories" — SCAs typically
handle everything, banks are narrower.

## Notes

- `reasonKey` must be one of `partners.eligibility.*` (`healthy`, `limitedFunds`, `highNpa`,
  `unknown`), so the reason renders in the user's language. Unknown keys fall back to `unknown`.
- `npaPct`, `overdueAmount` and `unutilisedLimit` are optional and informational, and all three
  are currently absent from every record. Do not compute status from them on the client — the
  server owns the norms, which differ per partner type and will change.
- Partner **names** in this repo are verified; **fund figures are absent, not invented**,
  because NSFDC does not publish them. See `data-honesty.md`.
- Ranking is by distance among partners that pass the filters, not the other way round.
