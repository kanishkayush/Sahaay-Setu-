import { describe, expect, it } from 'vitest';
import { partnerSearchUiState } from './searchUiState';

describe('partnerSearchUiState', () => {
  it('does not treat nearby-without-location as an API error or as results', () => {
    const state = partnerSearchUiState({
      viewMode: 'nearby',
      locationAvailable: false,
      onlyAccepting: true,
      isLoading: false,
      isError: false,
      resultCount: 0,
    });
    expect(state).toEqual({ kind: 'idle-location-required' });
  });

  it('keeps API failure distinct from zero results', () => {
    const state = partnerSearchUiState({
      viewMode: 'all',
      locationAvailable: false,
      onlyAccepting: true,
      isLoading: false,
      isError: true,
      resultCount: 0,
    });
    expect(state.kind).toBe('error');
  });

  it('treats accepting-only zero as a valid empty result', () => {
    const state = partnerSearchUiState({
      viewMode: 'all',
      locationAvailable: false,
      onlyAccepting: true,
      isLoading: false,
      isError: false,
      resultCount: 0,
    });
    expect(state).toEqual({ kind: 'empty', reason: 'accepting' });
  });

  it('all partners with results reports the filtered count', () => {
    const state = partnerSearchUiState({
      viewMode: 'all',
      locationAvailable: false,
      onlyAccepting: false,
      isLoading: false,
      isError: false,
      resultCount: 65,
    });
    expect(state).toEqual({ kind: 'results', count: 65 });
  });

  it('does not convert nearby-without-coordinates into all-partners results', () => {
    const nearby = partnerSearchUiState({
      viewMode: 'nearby',
      locationAvailable: false,
      onlyAccepting: false,
      isLoading: false,
      isError: false,
      resultCount: 65,
    });
    expect(nearby).toEqual({ kind: 'idle-location-required' });
  });
});
