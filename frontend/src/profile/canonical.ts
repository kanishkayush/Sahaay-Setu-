import type { UserProfile } from '@/api/contracts';
import { isValidCoordinate } from '@/utils/geo';

/** Unknown / missing is distinct from false. */
export function formatTriBool(value: boolean | null | undefined): string {
  if (value === true) return 'Yes';
  if (value === false) return 'No';
  return 'Not provided';
}

export function formatProvided(value: string | number | null | undefined, prefix = ''): string {
  if (value === null || value === undefined || value === '') return 'Not provided';
  return `${prefix}${value}`;
}

export function profileHasCoordinates(profile: UserProfile | undefined | null): boolean {
  return isValidCoordinate(profile?.address?.coordinates);
}

export function formatProfileLocation(profile: UserProfile | undefined | null): string {
  const address = profile?.address;
  const parts = [address?.addressLine1, address?.city, address?.district, address?.state, address?.pinCode]
    .filter((part): part is string => Boolean(part && String(part).trim()));
  if (parts.length) return parts.join(' · ');
  const coords = address?.coordinates;
  if (isValidCoordinate(coords)) {
    return `${coords.latitude.toFixed(4)}, ${coords.longitude.toFixed(4)}`;
  }
  return '';
}
