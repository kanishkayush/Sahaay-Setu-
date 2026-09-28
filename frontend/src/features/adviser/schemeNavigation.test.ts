import { describe, expect, it } from 'vitest';
import { schemeDetailPath } from './schemeNavigation';

describe('schemeDetailPath', () => {
  it('uses the same Find Scheme route and canonical scheme id', () => {
    expect(schemeDetailPath('nsfdc-term-loan')).toBe('/scheme/nsfdc-term-loan');
    expect(schemeDetailPath('nsfdc-uny')).toBe('/scheme/nsfdc-uny');
    expect(schemeDetailPath('nsfdc-education')).toBe('/scheme/nsfdc-education');
  });
});
