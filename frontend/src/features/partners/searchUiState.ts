export type PartnerSearchUiState =
  | { kind: 'idle-location-required' }
  | { kind: 'loading' }
  | { kind: 'error' }
  | { kind: 'empty'; reason: 'accepting' | 'nearby' | 'all' }
  | { kind: 'results'; count: number };

export function partnerSearchUiState(input: {
  viewMode: 'nearby' | 'all';
  locationAvailable: boolean;
  onlyAccepting: boolean;
  isLoading: boolean;
  isError: boolean;
  resultCount: number;
}): PartnerSearchUiState {
  const nearbyNeedsLocation = input.viewMode === 'nearby' && !input.locationAvailable;
  if (nearbyNeedsLocation) return { kind: 'idle-location-required' };
  if (input.isLoading) return { kind: 'loading' };
  if (input.isError) return { kind: 'error' };
  if (input.resultCount === 0) {
    if (input.onlyAccepting) return { kind: 'empty', reason: 'accepting' };
    return { kind: 'empty', reason: input.viewMode === 'all' ? 'all' : 'nearby' };
  }
  return { kind: 'results', count: input.resultCount };
}
