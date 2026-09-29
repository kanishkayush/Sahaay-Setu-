import { describe, expect, it } from 'vitest';
import { AssistantQueryResponseSchema, AssistantUICardSchema } from './assistant';

describe('education adviser cards', () => {
  it('accepts verified and unverified scheme cards with organization labels', () => {
    const verified = AssistantUICardSchema.parse({
      type: 'SCHEME_CARD',
      schemeId: 'nsfdc-education',
      schemeName: 'Educational Loan Scheme',
      organization: 'NSFDC',
      assistanceType: 'LOAN',
      verificationStatus: 'VERIFIED',
      amountFit: 'WITHIN_RANGE',
      incomeFit: 'WITHIN_LIMIT',
      courseFit: 'MATCH',
      whySelected: [{ kind: 'MATCH', text: 'Your family income is within the published ceiling.' }],
      isPrimary: true,
      action: 'VIEW_DETAILS',
      reason: 'Most relevant based on the information provided',
    });
    expect(verified.verificationStatus).toBe('VERIFIED');

    const unverified = AssistantUICardSchema.parse({
      type: 'SCHEME_CARD',
      schemeId: 'some-id',
      schemeName: 'Some Scholarship',
      organization: 'MINISTRY/DEPARTMENT',
      assistanceType: 'SCHOLARSHIP',
      verificationStatus: 'UNVERIFIED',
      reason: 'Verification required',
    });
    expect(unverified.verificationStatus).toBe('UNVERIFIED');
    expect(unverified.assistanceType).toBe('SCHOLARSHIP');
  });

  it('accepts a factual comparison card', () => {
    const card = AssistantUICardSchema.parse({
      type: 'COMPARISON_CARD',
      title: 'Comparison',
      rows: [
        {
          schemeName: 'Educational Loan Scheme',
          assistanceType: 'LOAN',
          amountFit: 'WITHIN_RANGE',
          incomeFit: 'WITHIN_LIMIT',
          verificationStatus: 'VERIFIED',
          schemeId: 'nsfdc-education',
        },
      ],
    });
    expect(card.rows[0]?.schemeId).toBe('nsfdc-education');
  });

  it('keeps a full assistant payload valid when education extras are present', () => {
    const parsed = AssistantQueryResponseSchema.parse({
      messageId: 'm1',
      answer: 'NSFDC Educational Loan Scheme is the main verified loan option.',
      answerLanguage: 'en',
      uiCards: [
        {
          type: 'SCHEME_CARD',
          schemeId: 'nsfdc-education',
          schemeName: 'Educational Loan Scheme',
          organization: 'NSFDC',
          assistanceType: 'LOAN',
          verificationStatus: 'VERIFIED',
        },
      ],
    });
    expect(parsed.uiCards).toHaveLength(1);
  });

  it('accepts the canonical VIEW_DETAILS scheme-card contract', () => {
    const card = AssistantUICardSchema.parse({
      type: 'SCHEME_CARD',
      schemeId: 'nsfdc-term-loan',
      schemeName: 'Term Loan',
      organization: 'NSFDC',
      domain: 'BUSINESS',
      assistanceType: 'LOAN',
      verificationStatus: 'VERIFIED',
      fitStatus: 'MOST_RELEVANT',
      whySelected: [
        { kind: 'MATCH', text: 'Your family income is within the published ceiling of ₹5 lakh.' },
        { kind: 'INFO', text: 'SC/ST certificate confirmation is required.' },
      ],
      amountFit: 'WITHIN_RANGE',
      incomeFit: 'WITHIN_LIMIT',
      maxLoanAmount: 4500000,
      interestRatePct: 8,
      maxTenureMonths: 84,
      isPrimary: true,
      action: 'VIEW_DETAILS',
      genderFit: 'UNKNOWN',
      purposeFit: 'MATCH',
    });
    expect(card.schemeId).toBe('nsfdc-term-loan');
    expect(card.action).toBe('VIEW_DETAILS');
    expect(card.whySelected?.[0]?.kind).toBe('MATCH');
  });

  it('accepts RELATED scheme cards that are not primary', () => {
    const card = AssistantUICardSchema.parse({
      type: 'SCHEME_CARD',
      schemeId: 'nsfdc-term-loan',
      schemeName: 'Term Loan',
      organization: 'NSFDC',
      domain: 'BUSINESS',
      assistanceType: 'LOAN',
      verificationStatus: 'VERIFIED',
      fitStatus: 'RELATED',
      isPrimary: false,
      action: 'VIEW_DETAILS',
      whySelected: [{ kind: 'INFO', text: 'This is a related general NSFDC credit product.' }],
    });
    expect(card.fitStatus).toBe('RELATED');
    expect(card.isPrimary).toBe(false);
    expect(card.action).toBe('VIEW_DETAILS');
  });
});
