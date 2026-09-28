import { describe, expect, it } from 'vitest';

import { MOCK_SCHEMES } from '@/api/mock/fixtures/schemes';
import { recommendSchemes } from './ruleEngine';
import type { ApplicantProfile } from '@/api/contracts';

const base: Omit<ApplicantProfile, 'projectType'> = {
  estimatedProjectCost: 200000,
  annualFamilyIncome: 300000,
  educationStatus: 'VOCATIONAL',
  gender: 'MALE',
};

describe('offline agriculture relevance', () => {
  it('does not promote Term Loan as a crop/agriculture match', () => {
    const result = recommendSchemes(MOCK_SCHEMES, { ...base, projectType: 'AGRICULTURE' });
    const primaryIds = result.recommendations.map((r) => r.scheme.id);
    expect(primaryIds).not.toContain('nsfdc-term-loan');
    expect(result.recommendations.every((r) => r.fitStatus !== 'RELATED')).toBe(true);
    for (const related of result.relatedOptions) {
      expect(related.fitStatus).toBe('RELATED');
      expect(related.scheme.id).not.toBe('nsfdc-education');
    }
  });

  it('does not promote Term Loan for dairy/livestock without evidence', () => {
    const result = recommendSchemes(MOCK_SCHEMES, { ...base, projectType: 'ANIMAL_HUSBANDRY' });
    expect(result.recommendations.map((r) => r.scheme.id)).not.toContain('nsfdc-term-loan');
  });

  it('still recommends NSFDC business credit for a business loan', () => {
    const result = recommendSchemes(MOCK_SCHEMES, { ...base, projectType: 'RETAIL_SHOP' });
    const ids = result.recommendations.map((r) => r.scheme.id);
    expect(ids.some((id) => ['nsfdc-term-loan', 'nsfdc-uny', 'nsfdc-mfs', 'nsfdc-amy'].includes(id))).toBe(true);
    expect(ids).not.toContain('nsfdc-education');
  });

  it('keeps the education catalogue for education loans', () => {
    const result = recommendSchemes(MOCK_SCHEMES, {
      ...base,
      projectType: 'EDUCATION',
      educationStatus: 'GRADUATE',
      estimatedProjectCost: 400000,
    });
    expect(result.recommendations.map((r) => r.scheme.id)).toContain('nsfdc-education');
    expect(result.recommendations.map((r) => r.scheme.id)).not.toContain('nsfdc-term-loan');
  });
});
