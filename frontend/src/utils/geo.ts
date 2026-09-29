import type { GeoPoint } from '@/api/contracts';

function toFiniteNumber(value: unknown): number | null {
  if (typeof value === 'number' && Number.isFinite(value)) return value;
  if (typeof value === 'string' && value.trim() !== '') {
    const parsed = Number(value);
    if (Number.isFinite(parsed)) return parsed;
  }
  return null;
}

/**
 * Safely validates a coordinate payload.
 * Rejects 0,0, NaN, Infinity, out-of-bounds, and non-numeric inputs.
 * Numeric strings from JSON/storage are coerced.
 */
export function isValidCoordinate(loc: unknown): loc is GeoPoint {
  if (!loc || typeof loc !== 'object') return false;
  const latitude = toFiniteNumber((loc as { latitude?: unknown }).latitude);
  const longitude = toFiniteNumber((loc as { longitude?: unknown }).longitude);
  if (latitude === null || longitude === null) return false;
  if (latitude < -90 || latitude > 90) return false;
  if (longitude < -180 || longitude > 180) return false;
  if (latitude === 0 && longitude === 0) return false;
  return true;
}

export function asGeoPoint(loc: unknown): GeoPoint | null {
  if (!isValidCoordinate(loc)) return null;
  return {
    latitude: toFiniteNumber((loc as { latitude: unknown }).latitude) as number,
    longitude: toFiniteNumber((loc as { longitude: unknown }).longitude) as number,
  };
}

const EARTH_RADIUS_KM = 6371;

const toRad = (deg: number) => (deg * Math.PI) / 180;

/** Great-circle distance in km. Good enough for "nearest branch" ranking. */
export function haversineKm(a: GeoPoint, b: GeoPoint): number {
  const dLat = toRad(b.latitude - a.latitude);
  const dLon = toRad(b.longitude - a.longitude);
  const lat1 = toRad(a.latitude);
  const lat2 = toRad(b.latitude);

  const h = Math.sin(dLat / 2) ** 2 + Math.sin(dLon / 2) ** 2 * Math.cos(lat1) * Math.cos(lat2);
  return 2 * EARTH_RADIUS_KM * Math.asin(Math.min(1, Math.sqrt(h)));
}

export function formatDistance(km: number | undefined): string {
  if (km === undefined) return '';
  if (km < 1) return `${Math.round(km * 1000)} m`;
  if (km < 10) return `${km.toFixed(1)} km`;
  return `${Math.round(km)} km`;
}
