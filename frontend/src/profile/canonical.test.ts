import { describe, expect, it } from 'vitest';
import { UserProfileSchema } from '../api/contracts/profile';
import { formatProfileLocation, profileHasCoordinates, profileSearchPoint, normalizeProfileLocation } from './canonical';

const parse = (address: unknown) =>
  UserProfileSchema.parse({ user_id: 'u1', address });

describe('profileSearchPoint', () => {
  it('returns the saved coordinates from a live profile payload', () => {
    const profile = parse({
      pinCode: '302017',
      district: 'Jaipur',
      state: 'Rajasthan',
      city: 'Jaipur',
      addressLine1: null,
      coordinates: { latitude: 26.9124, longitude: 75.7873 },
    });
    expect(profileSearchPoint(profile)).toEqual({ latitude: 26.9124, longitude: 75.7873 });
    expect(profileHasCoordinates(profile)).toBe(true);
  });

  it('counts coordinates alone as a set location', () => {
    const profile = parse({ coordinates: { latitude: 26.9124, longitude: 75.7873 } });
    expect(profileSearchPoint(profile)).toEqual({ latitude: 26.9124, longitude: 75.7873 });
  });

  it('returns undefined when there are no coordinates', () => {
    expect(profileSearchPoint(parse({ pinCode: '302017' }))).toBeNull();
    expect(profileSearchPoint(parse({ coordinates: null }))).toBeNull();
    expect(profileSearchPoint(undefined)).toBeNull();
  });

  it('rejects null island as a location', () => {
    expect(profileSearchPoint(parse({ coordinates: { latitude: 0, longitude: 0 } }))).toBeNull();
  });

  it('coerces numeric strings from GET payloads', () => {
    const profile = parse({
      coordinates: { latitude: '26.9124', longitude: '75.7873' },
    });
    expect(profileSearchPoint(profile)).toEqual({ latitude: 26.9124, longitude: 75.7873 });
  });

  it('reads a nested location object when address.coordinates is missing', () => {
    const profile = UserProfileSchema.parse({
      user_id: 'u1',
      location: { latitude: 26.9124, longitude: 75.7873 },
    });
    expect(profileSearchPoint(profile)).toEqual({ latitude: 26.9124, longitude: 75.7873 });
  });
});

describe('formatProfileLocation', () => {
  it('prefers the human-readable address parts', () => {
    const profile = parse({
      pinCode: '302017',
      district: 'Jaipur',
      state: 'Rajasthan',
      addressLine1: null,
      coordinates: { latitude: 26.9124, longitude: 75.7873 },
    });
    expect(formatProfileLocation(profile)).toBe('Jaipur · Rajasthan · 302017');
  });

  it('falls back to coordinates when only coordinates are saved', () => {
    const profile = parse({ coordinates: { latitude: 26.9124, longitude: 75.7873 } });
    expect(formatProfileLocation(profile)).toBe('26.9124, 75.7873');
  });

  it('is empty only when nothing is saved', () => {
    expect(formatProfileLocation(parse({}))).toBe('');
  });
});

describe('Profile save → Partners search point', () => {
  it('lets Partners search from the same canonical GET payload after null-safe parse', () => {
    const saved = UserProfileSchema.parse({
      user_id: 'u1',
      address: {
        pinCode: '302017',
        district: 'Jaipur',
        state: 'Rajasthan',
        city: 'Jaipur',
        addressLine1: null,
        coordinates: { latitude: 26.9124, longitude: 75.7873 },
      },
      eligibility: { scEligibilityStatus: null, annualFamilyIncome: null },
      business: { existingBusiness: null, businessActivity: null },
      fullName: null,
    });
    const point = profileSearchPoint(saved);
    expect(point).toEqual({ latitude: 26.9124, longitude: 75.7873 });
    expect(formatProfileLocation(saved)).toContain('Jaipur');
  });
});
