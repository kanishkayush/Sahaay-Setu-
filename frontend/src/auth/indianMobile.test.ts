import { describe, expect, it } from 'vitest';
import { normalizeIndianMobile } from './indianMobile';

describe('normalizeIndianMobile', () => {
  it.each(['9876543210', '9123456789', '8123456789', '7012345678', '9999999999'])(
    'accepts %s',
    (mobile) => {
      expect(normalizeIndianMobile(mobile)).toBe(mobile);
    },
  );

  it('strips +91, spaces, and dashes', () => {
    expect(normalizeIndianMobile('+91 9876543210')).toBe('9876543210');
    expect(normalizeIndianMobile('+91-9876543210')).toBe('9876543210');
    expect(normalizeIndianMobile('98765 43210')).toBe('9876543210');
    expect(normalizeIndianMobile('09876543210')).toBe('9876543210');
    expect(normalizeIndianMobile('919876543210')).toBe('9876543210');
  });

  it.each(['1234567890', '5123456789', '987654321', '98765432101', 'abcdefghij', '', '   ', '99999999'])(
    'rejects %s',
    (mobile) => {
      expect(normalizeIndianMobile(mobile)).toBeNull();
    },
  );
});
