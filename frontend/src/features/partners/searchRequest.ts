import type { LanguageCode, PartnerSearchRequest, GeoPoint } from '@/api/contracts';

export function buildPartnerSearchRequest(input: {
  viewMode: 'nearby' | 'all';
  location: GeoPoint | null;
  radiusKm: number;
  onlyAccepting: boolean;
  language: LanguageCode;
}): PartnerSearchRequest {
  if (input.viewMode === 'nearby') {
    if (!input.location) {
      return {
        radiusKm: input.radiusKm,
        allPartners: false,
        onlyAccepting: input.onlyAccepting,
        language: input.language,
      };
    }
    const request: PartnerSearchRequest = {
      location: input.location,
      radiusKm: input.radiusKm,
      allPartners: false,
      onlyAccepting: input.onlyAccepting,
      language: input.language,
    };
    if (!request.location) {
      throw new Error('Nearby search omitted saved profile coordinates');
    }
    return request;
  }

  return {
    location: input.location ?? undefined,
    radiusKm: 1000,
    allPartners: true,
    onlyAccepting: input.onlyAccepting,
    language: input.language,
  };
}

export function nearbyRequestMustIncludeCoordinates(
  viewMode: 'nearby' | 'all',
  location: GeoPoint | null,
  request: PartnerSearchRequest,
): boolean {
  if (viewMode !== 'nearby' || !location) return true;
  return Boolean(request.location?.latitude && request.location?.longitude);
}
