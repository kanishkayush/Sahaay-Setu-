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
      reason: 'Up to ₹40 lakh*',
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
});
