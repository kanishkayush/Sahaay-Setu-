/** Partner catalogue filters matching backend/app/partner_filters.py.

Live channel_partners.json has stateCode, eligibility.status, and optional
npaPct / unutilisedLimit / utilizedAmount / allocatedAmount. Missing figures
stay unknown. NPA, utilisation, and accepting status are independent.
*/

export type NpaBucket = 'all' | 'unknown' | 'acceptable' | 'concern';
export type UtilBucket = 'all' | 'unknown' | 'low' | 'medium' | 'high';
export type PartnerSortKey = 'distance' | 'name' | 'type' | 'state';

export const NSFDC_UTILISATION_RELEASE_PCT = 80;
export const UTILISATION_LOW_MEDIUM_SPLIT_PCT = 50;

export const IN_STATE_NAMES: Record<string, string> = {
  AP: 'Andhra Pradesh',
  AR: 'Arunachal Pradesh',
  AS: 'Assam',
  BR: 'Bihar',
  CG: 'Chhattisgarh',
  DL: 'Delhi',
  GJ: 'Gujarat',
  HP: 'Himachal Pradesh',
  HR: 'Haryana',
  JH: 'Jharkhand',
  JK: 'Jammu and Kashmir',
  KA: 'Karnataka',
  MH: 'Maharashtra',
  MN: 'Manipur',
  MP: 'Madhya Pradesh',
  MZ: 'Mizoram',
  OD: 'Odisha',
  PB: 'Punjab',
  RJ: 'Rajasthan',
  TN: 'Tamil Nadu',
  TS: 'Telangana',
  UP: 'Uttar Pradesh',
  WB: 'West Bengal',
  XX: 'Unknown / not coded',
};

const NAME_TO_CODE = Object.fromEntries(
  Object.entries(IN_STATE_NAMES).map(([code, name]) => [name.toLowerCase(), code]),
);

export type FilterablePartner = {
  name?: string;
  type?: string;
  stateCode?: string;
  distanceKm?: number | null;
  eligibility?: {
    status?: string;
    reasonKey?: string;
    npaPct?: number;
    utilizedAmount?: number;
    allocatedAmount?: number;
    unutilisedLimit?: number;
  };
};

export function normalizeStateCode(raw: string | null | undefined): string {
  if (raw == null) return 'XX';
  const text = String(raw).trim();
  if (!text) return 'XX';
  const upper = text.toUpperCase();
  if (upper.length === 2 && IN_STATE_NAMES[upper]) return upper;
  return NAME_TO_CODE[text.toLowerCase()] ?? 'XX';
}

export function stateDisplayName(code: string): string {
  return IN_STATE_NAMES[normalizeStateCode(code)] ?? 'Unknown / not coded';
}

function eligibility(partner: FilterablePartner) {
  return partner.eligibility ?? {};
}

export function npaBucket(partner: FilterablePartner): Exclude<NpaBucket, 'all'> {
  const elig = eligibility(partner);
  if (elig.npaPct == null) return 'unknown';
  const value = Number(elig.npaPct);
  if (!Number.isFinite(value)) return 'unknown';
  const partnerType = partner.type ?? '';
  if (partnerType === 'RRB') return value >= 15 ? 'concern' : 'acceptable';
  if (partnerType === 'NBFC_MFI' || partnerType === 'NBFC') {
    return value >= 0.5 ? 'concern' : 'acceptable';
  }
  if (elig.reasonKey === 'partners.eligibility.highNpa') return 'concern';
  return 'acceptable';
}

export function utilizationPct(partner: FilterablePartner): number | null {
  const elig = eligibility(partner);
  if (elig.utilizedAmount == null || elig.allocatedAmount == null) return null;
  const denom = Number(elig.allocatedAmount);
  const numer = Number(elig.utilizedAmount);
  if (!Number.isFinite(denom) || !Number.isFinite(numer) || denom <= 0) return null;
  return (numer / denom) * 100;
}

export function utilizationBucket(partner: FilterablePartner): Exclude<UtilBucket, 'all'> {
  const pct = utilizationPct(partner);
  if (pct == null) return 'unknown';
  if (pct >= NSFDC_UTILISATION_RELEASE_PCT) return 'high';
  if (pct >= UTILISATION_LOW_MEDIUM_SPLIT_PCT) return 'medium';
  return 'low';
}

export function applyPartnerFilters<T extends FilterablePartner>(
  partners: T[],
  input: {
    stateCode?: string | null;
    npa?: NpaBucket;
    utilization?: UtilBucket;
    onlyAccepting?: boolean;
  },
): T[] {
  const rawState = (input.stateCode ?? '').trim();
  const wantedState = rawState && rawState.toUpperCase() !== 'ALL' ? normalizeStateCode(rawState) : null;
  const npa = input.npa ?? 'all';
  const utilization = input.utilization ?? 'all';
  return partners.filter((partner) => {
    if (wantedState && normalizeStateCode(partner.stateCode) !== wantedState) return false;
    if (npa !== 'all' && npaBucket(partner) !== npa) return false;
    if (utilization !== 'all' && utilizationBucket(partner) !== utilization) return false;
    if (input.onlyAccepting) {
      const status = eligibility(partner).status || 'UNKNOWN';
      if (status !== 'ACCEPTING') return false;
    }
    return true;
  });
}

export function sortPartners<T extends FilterablePartner>(
  partners: T[],
  sortBy: PartnerSortKey,
  locationAvailable = true,
): T[] {
  const items = [...partners];
  if (sortBy === 'distance' && locationAvailable) {
    items.sort((a, b) => {
      const dA = a.distanceKm ?? Number.POSITIVE_INFINITY;
      const dB = b.distanceKm ?? Number.POSITIVE_INFINITY;
      if (dA !== dB) return dA - dB;
      return (a.name ?? '').localeCompare(b.name ?? '');
    });
    return items;
  }
  if (sortBy === 'type') {
    items.sort((a, b) => (a.type ?? '').localeCompare(b.type ?? '') || (a.name ?? '').localeCompare(b.name ?? ''));
    return items;
  }
  if (sortBy === 'state') {
    items.sort(
      (a, b) =>
        stateDisplayName(a.stateCode ?? 'XX').localeCompare(stateDisplayName(b.stateCode ?? 'XX')) ||
        (a.name ?? '').localeCompare(b.name ?? ''),
    );
    return items;
  }
  items.sort((a, b) => (a.name ?? '').localeCompare(b.name ?? ''));
  return items;
}

export function availableStates(partners: FilterablePartner[]): { code: string; name: string; count: number }[] {
  const seen = new Map<string, number>();
  for (const partner of partners) {
    const code = normalizeStateCode(partner.stateCode);
    seen.set(code, (seen.get(code) ?? 0) + 1);
  }
  return [...seen.entries()]
    .map(([code, count]) => ({ code, name: stateDisplayName(code), count }))
    .sort((a, b) => a.name.localeCompare(b.name));
}

export function selectedFilterAppearance(tokens: {
  controlSelectedBackground: string;
  controlSelectedText: string;
  inverse: string;
  surface: string;
}) {
  return {
    backgroundColor: tokens.controlSelectedBackground,
    color: tokens.controlSelectedText,
    isInverseOnWhite: tokens.controlSelectedBackground === tokens.inverse && tokens.controlSelectedText === '#FFFFFF',
    isWhiteOnWhite:
      tokens.controlSelectedBackground.toLowerCase() === '#ffffff' &&
      tokens.controlSelectedText.toLowerCase() === '#ffffff',
  };
}
