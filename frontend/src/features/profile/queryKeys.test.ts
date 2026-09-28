import { describe, expect, it } from 'vitest';
import { profileKeys } from './queryKeys';

describe('profileKeys', () => {
  it('uses one canonical profile query key shared by Profile and Partners', () => {
    expect(profileKeys.profile).toEqual(['profile']);
    expect(profileKeys.documents).toEqual(['profile', 'documents']);
  });
});
