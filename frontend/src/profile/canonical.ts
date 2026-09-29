import type { GeoPoint, ProfileAddress, UserProfile } from '@/api/contracts';
import { asGeoPoint, isValidCoordinate } from '@/utils/geo';

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

type LocationCarrier = {
  address?: ProfileAddress | null;
  location?: { latitude?: unknown; longitude?: unknown } | null;
  latitude?: unknown;
  longitude?: unknown;
};

/**
 * ONE canonical profile location. Prefers address.coordinates, then a nested
 * location object, then top-level lat/lng. Returns coordinates only when both
 * are valid finite numbers in range (and not 0,0).
 */
export function normalizeProfileLocation(
  profile: LocationCarrier | UserProfile | undefined | null,
): GeoPoint | null {
  if (!profile) return null;
  const nested = asGeoPoint(profile.address?.coordinates);
  if (nested) return nested;
  const locationObj = asGeoPoint(profile.location);
  if (locationObj) return locationObj;
  return asGeoPoint({ latitude: profile.latitude, longitude: profile.longitude });
}

export function profileHasCoordinates(profile: UserProfile | undefined | null): boolean {
  return normalizeProfileLocation(profile) !== null;
}

/**
 * Coordinates are the only thing distance search needs. A profile with
 * coordinates but no PIN/district/state still counts as "location set".
 */
export function profileSearchPoint(profile: UserProfile | undefined | null): GeoPoint | null {
  return normalizeProfileLocation(profile);
}

export function formatProfileLocation(profile: UserProfile | undefined | null): string {
  const address = profile?.address;
  const parts = [address?.addressLine1, address?.city, address?.district, address?.state, address?.pinCode]
    .filter((part): part is string => Boolean(part && String(part).trim()));
  if (parts.length) return parts.join(' · ');
  const coords = normalizeProfileLocation(profile);
  if (coords) {
    return `${coords.latitude.toFixed(4)}, ${coords.longitude.toFixed(4)}`;
  }
  return '';
}

export function profileHasAddressText(profile: UserProfile | undefined | null): boolean {
  const address = profile?.address;
  return Boolean(
    address?.pinCode ||
      address?.city ||
      address?.district ||
      address?.state ||
      address?.addressLine1,
  );
}

export { isValidCoordinate };
