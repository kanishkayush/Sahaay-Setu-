/** Indian mobile normalisation for hackathon login. */

export const INDIAN_MOBILE_RE = /^[6-9][0-9]{9}$/;

export function normalizeIndianMobile(raw: string | null | undefined): string | null {
  if (raw == null) return null;
  let digits = String(raw).replace(/\D/g, '');
  if (!digits) return null;
  if (digits.startsWith('91') && digits.length === 12) {
    digits = digits.slice(2);
  } else if (digits.startsWith('0') && digits.length === 11) {
    digits = digits.slice(1);
  }
  return INDIAN_MOBILE_RE.test(digits) ? digits : null;
}
