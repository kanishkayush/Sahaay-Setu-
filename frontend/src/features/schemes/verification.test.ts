import { describe, expect, it } from 'vitest';
import {
  isSchemeFinancialConfirmed,
  officialSourceUrl,
  ragVerificationBadge,
  schemeVerificationBadge,
  schemeVerificationKind,
  verifiedNumericDisplay,
} from './verification';

describe('scheme verification semantics', () => {
  it('does not treat unverified as fake, but also not as verified', () => {
    expect(schemeVerificationKind({ verified: false })).toBe('UNVERIFIED');
    expect(schemeVerificationKind({ verified: false, verificationStatus: 'UNVERIFIED' })).toBe('UNVERIFIED');
    expect(schemeVerificationKind({ verified: false, verificationStatus: 'STATUS_UNCLEAR' })).toBe('PARTIAL');
    expect(schemeVerificationKind({ verified: true, verificationStatus: 'VERIFIED' })).toBe('VERIFIED');
    expect(schemeVerificationBadge('UNVERIFIED')).toBe('VERIFICATION REQUIRED');
    expect(schemeVerificationBadge('PARTIAL')).toBe('PARTIAL — VERIFICATION REQUIRED');
    expect(ragVerificationBadge('UNVERIFIED')).toBe('VERIFICATION REQUIRED');
    expect(ragVerificationBadge('PARTIAL')).toBe('PARTIAL');
    expect(ragVerificationBadge('VERIFIED')).toBe('VERIFIED');
  });

  it('does not invent financial values for unverified schemes', () => {
    const unverified = { verified: false, verificationStatus: 'UNVERIFIED' };
    expect(isSchemeFinancialConfirmed(unverified)).toBe(false);
    expect(verifiedNumericDisplay(unverified, 0, (value) => `₹${value}`, 'Not verified')).toBe('Not verified');
    expect(verifiedNumericDisplay(unverified, 140000, (value) => `₹${value}`, 'Not verified')).toBe('Not verified');
    expect(verifiedNumericDisplay({ verified: true, verificationStatus: 'VERIFIED' }, 140000, (value) => `₹${value}`, 'Not verified')).toBe('₹140000');
  });

  it('only returns existing official source URLs', () => {
    expect(officialSourceUrl({})).toBeNull();
    expect(officialSourceUrl({ sourceUrl: 'https://nsfdc.nic.in/en/schemes/' })).toBe('https://nsfdc.nic.in/en/schemes/');
    expect(officialSourceUrl({ officialUrl: 'not-a-url' })).toBeNull();
  });
});
