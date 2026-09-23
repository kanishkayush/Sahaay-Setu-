# rule-education-exclusivity

**Education loans are only for education; business loans are never for course fees. The gate
runs in both directions.**

## Why it matters

These are different products with different documents, different repayment structures and
different partner types. Showing a term loan to a student asking about fees — or an education
loan to someone buying a sewing machine — is precisely the misrouted application the platform
exists to prevent. The applicant only discovers the mismatch at the branch.

## Wrong

```ts
// one direction only
if (scheme.category === 'EDUCATION_LOAN' && profile.projectType !== 'EDUCATION') {
  return null;
}
// → a student asking about fees still sees Term Loan and Micro Credit in their results
```

## Right

```ts
const isEducationScheme = scheme.category === 'EDUCATION_LOAN';
const wantsEducation = profile.projectType === 'EDUCATION';

if (isEducationScheme !== wantsEducation) {
  blockers.push(
    isEducationScheme
      ? reason(
          'MISMATCH',
          'This is an education loan — choose "Education" as your purpose',
          'यह शिक्षा ऋण है — उद्देश्य में "शिक्षा" चुनें',
        )
      : reason(
          'MISMATCH',
          'This is a business loan, not for course fees',
          'यह व्यवसाय ऋण है, पाठ्यक्रम शुल्क के लिए नहीं',
        ),
  );
}
```

The `!==` comparison is the whole rule: the two booleans must agree.

Note the first message is _actionable_ — it tells a student what to change, rather than just
excluding the scheme.

## The education-level sub-gate

Education schemes additionally require enough prior education for a professional or technical
course:

```ts
const rank = EDUCATION_RANK[profile.educationStatus] ?? 0;
if (rank >= 3) {                      // HIGHER_SECONDARY and above
  score += 20;
} else {
  blockers.push(reason('MISMATCH', 'Needs at least higher-secondary completion', …));
}
```

```
NONE 0 · PRIMARY 1 · SECONDARY 2 · HIGHER_SECONDARY 3 · VOCATIONAL 4 · GRADUATE 5 · POSTGRADUATE 6
```

Studying abroad additionally needs `GRADUATE` or above — encoded per-scheme in
`eligibilityRules`, not in the engine.

## Verified

```
Education, ₹8,00,000, graduate, female
→ NSFDC-EDU-IN (100) ₹7,20,000 @5.5%     ← women's rate applied
→ NSFDC-EDU-AB (100) ₹7,20,000 @5.5%
nearMisses: Term Loan, MKY, MSY — all "This is a business loan, not for course fees"
```

## Notes

- `EDUCATION_RANK` lives in `ruleEngine.ts`. Adding an education status means adding it there,
  to `EducationStatusSchema`, and to the `education.*` i18n block.
- Education loans are processed by SCAs and PSBs only — RRBs and NBFC-MFIs do not handle them.
  That is `Scheme.channelPartnerTypes`, and the partner locator respects it.
