import { describe, expect, it } from 'vitest';
import {
  applyPartnerFilters,
  availableStates,
  npaBucket,
  normalizeStateCode,
  selectedFilterAppearance,
  sortPartners,
  utilizationBucket,
} from './partnerFilters';
import { darkColors, lightColors } from '@/theme/palettes';

const partner = (
  overrides: Record<string, unknown> = {},
  eligibility: Record<string, unknown> = {},
) => ({
  name: 'Alpha',
  type: 'SCA',
  stateCode: 'RJ',
  eligibility: { status: 'UNKNOWN', reasonKey: 'partners.eligibility.unknown', ...eligibility },
  ...overrides,
});

describe('partnerFilters', () => {
  it('normalizes state names without aliasing distinct labels', () => {
    expect(normalizeStateCode('Rajasthan')).toBe('RJ');
    expect(normalizeStateCode('RAJASTHAN')).toBe('RJ');
    expect(normalizeStateCode('rajasthan')).toBe('RJ');
    expect(normalizeStateCode('West Bengal')).toBe('WB');
    expect(normalizeStateCode('Western Bengal')).toBe('XX');
  });

  it('filters and sorts by canonical state', () => {
    const partners = [
      partner({ id: 'b', name: 'B Partner', stateCode: 'RJ' }),
      partner({ id: 'a', name: 'A Partner', stateCode: 'rj' }),
      partner({ id: 'c', name: 'C Partner', stateCode: 'MH' }),
    ];
    const rajasthan = applyPartnerFilters(partners, { stateCode: 'Rajasthan' });
    expect(rajasthan.map((item) => item.id)).toEqual(['b', 'a']);
    const sorted = sortPartners(partners, 'state');
    expect(sorted.map((item) => item.id)).toEqual(['c', 'a', 'b']);
  });

  it('does not treat unknown NPA as acceptable or accepting', () => {
    const unknown = partner({ id: 'u' });
    const ok = partner({ id: 'ok', type: 'SCA' }, { npaPct: 2 });
    expect(npaBucket(unknown)).toBe('unknown');
    expect(npaBucket(ok)).toBe('acceptable');
    expect(applyPartnerFilters([unknown], { npa: 'acceptable' })).toEqual([]);
    expect(applyPartnerFilters([unknown], { onlyAccepting: true })).toEqual([]);
  });

  it('keeps utilization unknown unless both amount fields are valid', () => {
    expect(utilizationBucket(partner())).toBe('unknown');
    expect(utilizationBucket(partner({}, { utilizedAmount: 10, allocatedAmount: 0 }))).toBe('unknown');
    expect(utilizationBucket(partner({}, { utilizedAmount: 20, allocatedAmount: 100 }))).toBe('low');
    expect(utilizationBucket(partner({}, { utilizedAmount: 85, allocatedAmount: 100 }))).toBe('high');
  });

  it('combines state, NPA, utilisation, and accepting without fallback', () => {
    const partners = [
      partner({ id: 'hit', stateCode: 'RJ' }, { status: 'ACCEPTING', npaPct: 1, utilizedAmount: 20, allocatedAmount: 100 }),
      partner({ id: 'miss', stateCode: 'RJ' }),
      partner({ id: 'other', stateCode: 'MH' }, { status: 'ACCEPTING', npaPct: 1, utilizedAmount: 20, allocatedAmount: 100 }),
    ];
    const hits = applyPartnerFilters(partners, {
      stateCode: 'RJ',
      npa: 'acceptable',
      utilization: 'low',
      onlyAccepting: true,
    });
    expect(hits.map((item) => item.id)).toEqual(['hit']);
    expect(
      applyPartnerFilters(partners, {
        stateCode: 'RJ',
        npa: 'acceptable',
        utilization: 'high',
        onlyAccepting: true,
      }),
    ).toEqual([]);
    expect(availableStates(partners).some((state) => state.code === 'RJ')).toBe(true);
  });

  it('uses semantic selected tokens that are not white-on-white in dark mode', () => {
    const dark = selectedFilterAppearance(darkColors);
    const light = selectedFilterAppearance(lightColors);
    expect(dark.isWhiteOnWhite).toBe(false);
    expect(dark.backgroundColor).toBe(darkColors.controlSelectedBackground);
    expect(dark.color).toBe(darkColors.controlSelectedText);
    expect(light.backgroundColor).toBe(lightColors.controlSelectedBackground);
    expect(light.color).toBe(lightColors.controlSelectedText);
  });
});
