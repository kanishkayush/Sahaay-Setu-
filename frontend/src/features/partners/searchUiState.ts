export type PartnerSearchUiState =
  | { kind: 'loading-profile' }
  | { kind: 'profile-unavailable' }
  | { kind: 'idle-location-required' }
  | { kind: 'loading' }
  | { kind: 'error' }
  | { kind: 'empty'; reason: 'accepting' | 'nearby' | 'all' | 'filters' }
  | { kind: 'results'; count: number };

export function partnerSearchUiState(input: {
  viewMode: 'nearby' | 'all';
  locationAvailable: boolean;
  onlyAccepting: boolean;
  isLoading: boolean;
  isError: boolean;
  resultCount: number;
  profileStatus?: 'loading' | 'error' | 'ready';
  extraFiltersActive?: boolean;
}): PartnerSearchUiState {
  const profileStatus = input.profileStatus ?? 'ready';
  if (profileStatus === 'loading') return { kind: 'loading-profile' };
  if (profileStatus === 'error' && !input.locationAvailable) {
    return { kind: 'profile-unavailable' };
  }
  const nearbyNeedsLocation = input.viewMode === 'nearby' && !input.locationAvailable;
  if (nearbyNeedsLocation) return { kind: 'idle-location-required' };
  if (input.isLoading) return { kind: 'loading' };
  if (input.isError) return { kind: 'error' };
  if (input.resultCount === 0) {
    if (input.extraFiltersActive) return { kind: 'empty', reason: 'filters' };
    if (input.onlyAccepting) return { kind: 'empty', reason: 'accepting' };
    return { kind: 'empty', reason: input.viewMode === 'all' ? 'all' : 'nearby' };
  }
  return { kind: 'results', count: input.resultCount };
}
