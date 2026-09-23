import type { GeoPoint } from '@/api/contracts';

/** 
 * Safely validates a coordinate payload. 
 * Rejects 0,0, NaN, Infinity, and out-of-bounds inputs. 
 */
export function isValidCoordinate(loc: any): loc is GeoPoint {
  if (!loc || typeof loc !== 'object') return false;
  const { latitude, longitude } = loc;
  
  if (typeof latitude !== 'number' || typeof longitude !== 'number') return false;
  if (!Number.isFinite(latitude) || !Number.isFinite(longitude)) return false;
  
  if (latitude < -90 || latitude > 90) return false;
  if (longitude < -180 || longitude > 180) return false;
  
  // Exclude 0,0 which is commonly used as a default/null island.
  if (latitude === 0 && longitude === 0) return false;
  
  return true;
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
