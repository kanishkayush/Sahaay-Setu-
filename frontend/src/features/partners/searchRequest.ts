import type { LanguageCode, PartnerSearchRequest, GeoPoint } from '@/api/contracts';
import type { NpaBucket, PartnerSortKey, UtilBucket } from './partnerFilters';

export function buildPartnerSearchRequest(input: {
  viewMode: 'nearby' | 'all';
  location: GeoPoint | null;
  radiusKm: number;
  onlyAccepting: boolean;
  language: LanguageCode;
  stateCode?: string | null;
  npaBucket?: NpaBucket;
  fundUtilizationBucket?: UtilBucket;
  sortBy?: PartnerSortKey;
}): PartnerSearchRequest {
  const filters = {
    onlyAccepting: input.onlyAccepting,
    language: input.language,
    stateCode: input.stateCode && input.stateCode !== 'ALL' ? input.stateCode : undefined,
    npaBucket: input.npaBucket && input.npaBucket !== 'all' ? input.npaBucket : undefined,
    fundUtilizationBucket:
      input.fundUtilizationBucket && input.fundUtilizationBucket !== 'all'
        ? input.fundUtilizationBucket
        : undefined,
    sortBy: input.sortBy,
  };

  if (input.viewMode === 'nearby') {
    if (!input.location) {
      return {
        radiusKm: input.radiusKm,
        allPartners: false,
        ...filters,
      };
    }
    const request: PartnerSearchRequest = {
      location: input.location,
      radiusKm: input.radiusKm,
      allPartners: false,
      ...filters,
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
    ...filters,
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
