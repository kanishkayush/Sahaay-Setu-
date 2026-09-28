import { describe, expect, it } from 'vitest';
import { UserProfileSchema } from './profile';
import { isValidCoordinate } from '../../utils/geo';

/**
 * The backend serialises unset optional fields as explicit `null`, not by
 * omitting them. `GET /v1/profile` returns `addressLine1: null` as soon as the
 * user saves a location whose reverse geocode had no street name. A contract
 * that only allowed `undefined` rejected the whole profile, so every screen
 * reading `['profile']` fell back to an empty profile and reported
 * "location not set" even though coordinates were stored.
 */
const PRODUCTION_PROFILE_PAYLOAD = {
  address: {
    pinCode: '302017',
    state: 'Rajasthan',
    district: 'Jaipur',
    city: 'Jaipur',
    addressLine1: null,
    coordinates: { latitude: 26.9124, longitude: 75.7873 },
  },
  user_id: '1b89c408-a111-5048-98c3-9fd57d662d40',
  updatedAt: '2026-09-28T17:34:00.660830+00:00',
  createdAt: '2026-09-27T11:05:36.789738+00:00',
  id: '04aa0ef5-1796-405d-a76c-a1aacdac0de9',
};

describe('UserProfileSchema', () => {
  it('accepts the live payload where unset address fields are null', () => {
    const parsed = UserProfileSchema.safeParse(PRODUCTION_PROFILE_PAYLOAD);
    expect(parsed.success).toBe(true);
    if (!parsed.success) return;
    expect(parsed.data.address?.coordinates).toEqual({ latitude: 26.9124, longitude: 75.7873 });
    expect(parsed.data.address?.pinCode).toBe('302017');
  });

  it('keeps coordinates usable for distance search after parsing', () => {
    const parsed = UserProfileSchema.parse(PRODUCTION_PROFILE_PAYLOAD);
    expect(isValidCoordinate(parsed.address?.coordinates)).toBe(true);
  });

  it('treats coordinates alone as a set location even without pin/district/state', () => {
    const parsed = UserProfileSchema.parse({
      user_id: 'u1',
      address: {
        pinCode: null,
        district: null,
        state: null,
        city: null,
        addressLine1: null,
        coordinates: { latitude: 26.9124, longitude: 75.7873 },
      },
    });
    expect(isValidCoordinate(parsed.address?.coordinates)).toBe(true);
  });

  it('treats a null coordinates field as no location rather than a parse failure', () => {
    const parsed = UserProfileSchema.safeParse({
      user_id: 'u1',
      address: { pinCode: '302017', coordinates: null },
    });
    expect(parsed.success).toBe(true);
    if (!parsed.success) return;
    expect(isValidCoordinate(parsed.data.address?.coordinates)).toBe(false);
  });

  it('accepts null business and personal fields', () => {
    const parsed = UserProfileSchema.safeParse({
      user_id: 'u1',
      fullName: null,
      business: { existingBusiness: null, businessActivity: null },
      eligibility: { scEligibilityStatus: null, annualFamilyIncome: null },
    });
    expect(parsed.success).toBe(true);
  });
});
