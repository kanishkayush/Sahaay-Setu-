import { describe, expect, it } from 'vitest';
import { buildPartnerSearchRequest, nearbyRequestMustIncludeCoordinates } from './searchRequest';

const JAIPUR = { latitude: 26.9124, longitude: 75.7873 };

describe('buildPartnerSearchRequest', () => {
  it('sends saved profile coordinates on Nearby', () => {
    const request = buildPartnerSearchRequest({
      viewMode: 'nearby',
      location: JAIPUR,
      radiusKm: 25,
      onlyAccepting: false,
      language: 'en',
    });
    expect(request.location).toEqual(JAIPUR);
    expect(request.allPartners).toBe(false);
    expect(request.radiusKm).toBe(25);
    expect(nearbyRequestMustIncludeCoordinates('nearby', JAIPUR, request)).toBe(true);
  });

  it('cannot make a coordinate-less Nearby request when a profile point exists', () => {
    const request = buildPartnerSearchRequest({
      viewMode: 'nearby',
      location: JAIPUR,
      radiusKm: 25,
      onlyAccepting: true,
      language: 'en',
    });
    expect(request.location).toBeDefined();
    expect(request.location?.latitude).toBe(JAIPUR.latitude);
    expect(request.allPartners).toBe(false);
  });

  it('does not invent coordinates for Nearby without a saved point', () => {
    const request = buildPartnerSearchRequest({
      viewMode: 'nearby',
      location: null,
      radiusKm: 25,
      onlyAccepting: false,
      language: 'en',
    });
    expect(request.location).toBeUndefined();
    expect(request.allPartners).toBe(false);
  });

  it('All Partners can run without coordinates', () => {
    const request = buildPartnerSearchRequest({
      viewMode: 'all',
      location: null,
      radiusKm: 25,
      onlyAccepting: false,
      language: 'en',
    });
    expect(request.allPartners).toBe(true);
    expect(request.location).toBeUndefined();
  });
});
