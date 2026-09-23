# flow-state-placement

**Server data lives in React Query. Only four things go in the zustand store. Everything else
is local component state.**

## Why it matters

Duplicating server data into a global store means two sources of truth that drift, plus
manual invalidation nobody maintains. Conversely, persisting things that should not survive a
restart — a half-finished wizard, a chat history — is both a privacy question and a source of
confusing stale UI.

## The store holds exactly this

```ts
language; // the single most important setting in this app
hasCompletedOnboarding;
profile; // the applicant's recommender answers, so they never retype them
savedSchemeIds;
```

That is `src/store/useAppStore.ts` in full. Adding a fifth thing needs a reason.

## Wrong

```tsx
// duplicating server data into the store
const setSchemes = useAppStore((s) => s.setSchemes);
useEffect(() => {
  listSchemes().then((r) => setSchemes(r.items)); // ← now two sources of truth
}, []);
```

```tsx
// persisting a conversation
persist((set) => ({ chatMessages: [] }), { name: 'sahaay.chat' }); // ← see Notes
```

## Right

```tsx
// server data — React Query owns caching, staleness and refetch
const { data } = useSchemes();

// device state — zustand, persisted
const language = useAppStore((s) => s.language);

// ephemeral UI state — local
const [showSchedule, setShowSchedule] = useState(false);
```

## Notes

- Rule of thumb: **if it can be re-fetched, it does not belong in the store.**
- Assistant chat history is deliberately session-scoped in `useAssistant`, not persisted. We do
  not keep a record of what people asked about their finances.
- The store persists via AsyncStorage. Everything in it stays on the device — see ADR-011.
- Cache policy belongs in the hook, not the screen: the scheme catalogue is cached an hour so
  it survives offline; partner fund-health is five minutes because it goes stale fast.
