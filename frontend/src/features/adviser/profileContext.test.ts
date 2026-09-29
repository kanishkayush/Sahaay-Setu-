import { describe, expect, it } from 'vitest';
import { buildAssistantProfileContext } from './profileContext';
import type { UserProfile } from '@/api/contracts';

const base: UserProfile = {
  id: 'p1',
  user_id: 'u1',
  savedSchemes: [],
  address: {},
  eligibility: {},
  business: {},
  preferences: { language: 'en' },
  createdAt: '',
  updatedAt: '',
};

describe('buildAssistantProfileContext', () => {
  it('omits empty profiles so chat does not send a wiping payload', () => {
    expect(buildAssistantProfileContext(base)).toBeUndefined();
    expect(buildAssistantProfileContext(undefined)).toBeUndefined();
  });

  it('passes saved income and SC without converting null to false', () => {
    const ctx = buildAssistantProfileContext({
      ...base,
      eligibility: { annualFamilyIncome: 300000, scEligibilityStatus: null },
    });
    expect(ctx).toEqual({ annualFamilyIncome: 300000 });
  });

  it('includes saved gender as a first-class profile signal', () => {
    const ctx = buildAssistantProfileContext({
      ...base,
      eligibility: { gender: 'FEMALE' },
    });
    expect(ctx).toEqual({ gender: 'FEMALE' });
  });

  it('includes coordinates only when they are a real location', () => {
    const none = buildAssistantProfileContext({
      ...base,
      address: { coordinates: { latitude: 0, longitude: 0 } },
    });
    expect(none).toBeUndefined();
    const ctx = buildAssistantProfileContext({
      ...base,
      address: { pinCode: '302017', coordinates: { latitude: 26.91, longitude: 75.78 } },
    });
    expect(ctx?.pinCode).toBe('302017');
    expect(ctx?.latitude).toBe(26.91);
  });
});
