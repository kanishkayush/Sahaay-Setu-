/** Canonical React Query keys. Profile and Partners must share `profile`. */
export const profileKeys = {
  profile: ['profile'] as const,
  documents: ['profile', 'documents'] as const,
};
