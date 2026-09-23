# endpoint-add

**Adding an endpoint is five steps. Skipping the mock breaks the "runs with no backend"
property the whole team depends on.**

## Why it matters

The app is demoable with zero servers because every endpoint has a mock. A service that only
has the HTTP branch turns `USE_MOCK_API=true` into a runtime crash — and that is the mode the
app ships in, the mode a judge sees, and the mode the frontend is developed in.

## The five steps

### 1. Route

```ts
// src/api/endpoints.ts
export const ENDPOINTS = {
  // …
  applications: {
    status: (id: string) => `/${API_VERSION}/applications/${encodeURIComponent(id)}`,
  },
} as const;
```

### 2. Schemas

```ts
// src/api/contracts/application.ts
export const ApplicationStatusSchema = z.object({
  id: z.string(),
  stage: z.enum(['SUBMITTED', 'UNDER_REVIEW', 'SANCTIONED', 'DISBURSED', 'REJECTED']),
  updatedAt: z.string(),
  partnerId: z.string().optional(),
});
export type ApplicationStatus = z.infer<typeof ApplicationStatusSchema>;
```

Export it from `src/api/contracts/index.ts`.

### 3. Mock — not optional

```ts
// src/api/mock/server.ts
export async function mockGetApplicationStatus(id: string): Promise<ApplicationStatus> {
  await delay();
  return { id, stage: 'UNDER_REVIEW', updatedAt: new Date().toISOString() };
}
```

### 4. Service — the `USE_MOCK_API` branch

```ts
// src/api/services/applications.service.ts
export async function getApplicationStatus(id: string): Promise<ApplicationStatus> {
  if (USE_MOCK_API) return mockGetApplicationStatus(id);
  return apiRequest(ENDPOINTS.applications.status(id), ApplicationStatusSchema);
}
```

Export it from `src/api/services/index.ts`.

### 5. Hook

```ts
// src/hooks/useApplication.ts
export function useApplicationStatus(id: string | undefined) {
  return useQuery({
    queryKey: ['applications', id],
    queryFn: () => getApplicationStatus(id!),
    enabled: Boolean(id),
    staleTime: 1000 * 60, // status changes; do not cache it for an hour
  });
}
```

Then document it in `docs/API_CONTRACT.md`.

## Should it fall back when the backend fails?

Depends on whether stale data can mislead.

| Endpoint           | Falls back?                                   | Why                                                                     |
| ------------------ | --------------------------------------------- | ----------------------------------------------------------------------- |
| `/recommendations` | **yes**, to the rule engine                   | A recommendation is better than a dead screen                           |
| `/assistant/query` | **yes**, to the offline KB, `grounded: false` | An honest partial answer beats nothing                                  |
| `/partners/search` | **no**                                        | Stale fund health would route someone to a branch that cannot help them |
| `/schemes`         | cache only                                    | React Query serves the last good response                               |

Fall back when a slightly worse answer still helps. Fail visibly when a stale answer could send
someone to the wrong place.

## Notes

- Pick a `staleTime` deliberately in the hook. The catalogue is cached an hour so it survives
  offline; partner fund-health is five minutes because it goes stale fast.
- Use `useMutation` for anything the user explicitly triggers and expects fresh each time — the
  recommender is a mutation for exactly this reason.
