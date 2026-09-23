# rule-income-ceiling

**Annual family income above ₹5,00,000 disqualifies the applicant. It is a gate, not a score.**

## Why it matters

This single number decides eligibility for the entire programme. Treating it as a soft signal
would recommend schemes to people who will be rejected at the branch — wasting a trip that may
cost a day's wages and a bus fare.

It is also the most common reason someone gets no results, so the _explanation_ matters as much
as the gate.

## Wrong

```ts
// scoring instead of gating
if (profile.annualFamilyIncome <= scheme.maxAnnualFamilyIncome) score += 25;
// → an over-ceiling applicant still gets recommendations, just ranked lower
```

```ts
// hardcoding the ceiling
if (profile.annualFamilyIncome > 500_000) return [];
// → the limit is per-scheme data; a future scheme with a different ceiling breaks silently
```

## Right

```ts
if (profile.annualFamilyIncome > scheme.maxAnnualFamilyIncome) {
  blockers.push(
    reason(
      'MISMATCH',
      `Annual family income must be under ${formatInr(scheme.maxAnnualFamilyIncome)}`,
      `वार्षिक पारिवारिक आय ${formatInr(scheme.maxAnnualFamilyIncome)} से कम होनी चाहिए`,
    ),
  );
} else {
  score += 25;
  reasons.push(reason('MATCH' /* … */));
}
```

Any scheme with a non-empty `blockers` array is excluded from `recommendations` and appears in
`nearMisses` with the reason attached.

## Verified behaviour

```
Profile: retail shop, ₹3,00,000 project, ₹9,00,000 income
→ recommendations: 0
→ nearMisses: every scheme, each with
   "Annual family income must be under ₹5,00,000"
```

## Notes

- **Family** income, not personal — the wizard copy says "total income of everyone in your
  household", because the distinction changes the answer.
- The ceiling is `Scheme.maxAnnualFamilyIncome`, per scheme. All current schemes use ₹5 lakh,
  but read it from the data.
- Zero results is a valid, useful outcome here. The results screen has a dedicated empty state
  explaining the ceiling rather than showing a bare "no matches".
