import { describe, expect, it } from 'vitest';
import { PartnerSearchResponseSchema } from './partner';

const samplePartner = {
  id: 'psb-1',
  name: 'Sample Bank',
  type: 'PSB',
  address: 'Somewhere',
  district: 'Unknown',
  stateCode: 'RJ',
  pincode: '302001',
  location: { latitude: 26.91, longitude: 75.78 },
  supportedSchemeCategories: [],
  eligibility: { status: 'UNKNOWN', reasonKey: 'partners.eligibility.unknown' },
  lastUpdatedAt: '2026-09-25T00:00:00.000Z',
};

describe('PartnerSearchResponseSchema', () => {
  it('accepts all-partners with no location (searchedFrom null)', () => {
    const parsed = PartnerSearchResponseSchema.safeParse({
      items: [samplePartner],
      fallbackUsed: false,
      searchedFrom: null,
      radiusKm: 1000,
    });
    expect(parsed.success).toBe(true);
    if (parsed.success) {
      expect(parsed.data.items).toHaveLength(1);
    }
  });

  it('accepts a valid empty accepting-only result as success, not a contract error', () => {
    const parsed = PartnerSearchResponseSchema.safeParse({
      items: [],
      fallbackUsed: false,
      searchedFrom: null,
      radiusKm: 1000,
    });
    expect(parsed.success).toBe(true);
    if (parsed.success) {
      expect(parsed.data.items).toEqual([]);
    }
  });
});
