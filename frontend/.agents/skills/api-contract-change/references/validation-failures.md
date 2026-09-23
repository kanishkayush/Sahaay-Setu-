# validation-failures

**A `ContractViolationError` means the response did not match the agreed shape. It names the
failing fields. Read it before changing anything.**

## Why it matters

This error is the reason the contract is Zod rather than TypeScript interfaces. Without it, a
backend returning `distance_km` instead of `distanceKm` produces `undefined` on screen and a
stack trace pointing at a component three layers away. With it, you get the path and the field.

The error is doing its job. Do not silence it.

## Reading the error

```
ContractViolationError: Response from /v1/partners/search did not match the agreed contract.
Fix the backend or update src/api/contracts. Issues: [
  {"code":"invalid_type","expected":"number","received":"undefined","path":["items",0,"distanceKm"]},
  {"code":"invalid_type","expected":"string","received":"undefined","path":["items",0,"lastUpdatedAt"]}
]
```

- **path** — exactly where. `["items", 0, "distanceKm"]` is the first item's `distanceKm`.
- **expected / received** — `received: "undefined"` means the field is absent or differently
  named. `received: "string"` where a number was expected usually means the backend is sending
  `"6.5"` instead of `6.5`.

## Wrong responses to it

```ts
// silencing it
const data = (await response.json()) as PartnerSearchResponse; // ← lying to the compiler
```

```ts
// making the schema permissive to make the error go away
items: z.array(z.any()),
```

Both trade a loud, precise failure for a silent, vague one.

## Right

Decide which side is wrong, then fix that side:

| Symptom                                                  | Likely cause                                  | Fix                                                     |
| -------------------------------------------------------- | --------------------------------------------- | ------------------------------------------------------- |
| `received: "undefined"` on a field the backend does send | naming mismatch (`snake_case` vs `camelCase`) | agree on one; the contract is camelCase                 |
| `received: "undefined"` on a field not built yet         | schema is ahead of the backend                | make it `.optional()` — see `field-add.md`              |
| `received: "string"`, expected number                    | serialisation, often a Decimal                | backend should send a JSON number                       |
| `invalid_enum_value`                                     | backend added a case                          | add it to the enum on both sides                        |
| Fails only sometimes                                     | field is genuinely nullable                   | `.nullable()` or `.optional()`, and handle it in the UI |

## Notes

- `ApiRequestError` is different — that is a non-2xx status with a structured `ApiError` body.
  A `ContractViolationError` means the request _succeeded_ and the body was wrong.
- Errors are validated too, via `ApiErrorSchema`. A malformed error body falls back to a
  synthesised one rather than throwing inside the error path.
- Include the full error text in bug reports — the issue paths usually identify the cause
  immediately. The issue template asks for it.
