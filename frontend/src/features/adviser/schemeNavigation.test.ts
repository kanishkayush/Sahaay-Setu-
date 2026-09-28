import { describe, expect, it } from 'vitest';
import { schemeDetailPath } from './schemeNavigation';

describe('schemeDetailPath', () => {
  it('uses the same Find Scheme route and canonical scheme id', () => {
    expect(schemeDetailPath('nsfdc-term-loan')).toBe('/scheme/nsfdc-term-loan');
    expect(schemeDetailPath('nsfdc-uny')).toBe('/scheme/nsfdc-uny');
    expect(schemeDetailPath('nsfdc-education')).toBe('/scheme/nsfdc-education');
    expect(schemeDetailPath('nsfdc-mfs')).toBe('/scheme/nsfdc-mfs');
    expect(schemeDetailPath('nsfdc-amy')).toBe('/scheme/nsfdc-amy');
  });

  it('is the single scheme-detail route for RAG cards and Check Eligibility', () => {
    const id = 'nsfdc-term-loan';
    expect(schemeDetailPath(id)).toBe(`/scheme/${id}`);
    expect(schemeDetailPath(id).startsWith('/scheme/')).toBe(true);
  });
});
