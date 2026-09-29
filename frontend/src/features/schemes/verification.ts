/** Scheme verification labels. UNVERIFIED is not fake/invalid/ineligible. */

export type SchemeVerificationKind = 'VERIFIED' | 'PARTIAL' | 'UNVERIFIED';

export type SchemeVerificationFields = {
  verified?: boolean;
  verificationStatus?: string | null;
};

export function schemeVerificationKind(scheme: SchemeVerificationFields): SchemeVerificationKind {
  const status = String(scheme.verificationStatus ?? '').toUpperCase();
  if (status === 'VERIFIED' && scheme.verified !== false) return 'VERIFIED';
  if (scheme.verified === true && (status === '' || status === 'VERIFIED')) return 'VERIFIED';
  if (status === 'PARTIAL' || status === 'STATUS_UNCLEAR') return 'PARTIAL';
  if (scheme.verified === true && status && status !== 'VERIFIED') return 'PARTIAL';
  if (scheme.verified === true) return 'VERIFIED';
  return 'UNVERIFIED';
}

export function schemeVerificationBadge(kind: SchemeVerificationKind): string {
  if (kind === 'VERIFIED') return 'VERIFIED';
  if (kind === 'PARTIAL') return 'PARTIAL — VERIFICATION REQUIRED';
  return 'VERIFICATION REQUIRED';
}

export function ragVerificationBadge(status?: string | null): string {
  const kind = String(status ?? '').toUpperCase();
  if (kind === 'VERIFIED') return 'VERIFIED';
  if (kind === 'PARTIAL') return 'PARTIAL';
  if (kind === 'UNVERIFIED') return 'VERIFICATION REQUIRED';
  return kind;
}

export function isSchemeFinancialConfirmed(scheme: SchemeVerificationFields): boolean {
  return schemeVerificationKind(scheme) === 'VERIFIED';
}

export function verifiedNumericDisplay(
  scheme: SchemeVerificationFields,
  value: number | null | undefined,
  format: (value: number) => string,
  unverifiedLabel: string,
): string {
  if (!isSchemeFinancialConfirmed(scheme)) return unverifiedLabel;
  if (value == null || !Number.isFinite(value)) return unverifiedLabel;
  return format(value);
}

export function officialSourceUrl(scheme: {
  sourceUrl?: string | null;
  officialUrl?: string | null;
  citations?: { url?: string }[];
}): string | null {
  for (const candidate of [scheme.sourceUrl, scheme.officialUrl, ...(scheme.citations ?? []).map((c) => c.url)]) {
    if (typeof candidate === 'string' && /^https?:\/\//i.test(candidate)) return candidate;
  }
  return null;
}
