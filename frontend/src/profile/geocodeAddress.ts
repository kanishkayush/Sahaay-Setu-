import type { GeoPoint, ProfileAddress } from '@/api/contracts';
import { asGeoPoint } from '@/utils/geo';

export type AddressLike = {
  pinCode?: string | null;
  city?: string | null;
  district?: string | null;
  state?: string | null;
  addressLine1?: string | null;
  coordinates?: GeoPoint | null;
};

/**
 * Forward-geocode a saved Indian address (PIN / city / state) via Nominatim.
 * This resolves the user's saved Profile address — it is not IP, GPS, or a
 * hardcoded city.
 */
export async function geocodeIndiaAddress(
  address: AddressLike | undefined | null,
  fetchImpl: typeof fetch = fetch,
): Promise<GeoPoint | null> {
  if (!address) return null;
  const pin = (address.pinCode || '').trim();
  const parts = [address.addressLine1, address.city, address.district, address.state]
    .map((part) => (part || '').trim())
    .filter(Boolean);
  if (!/^\d{6}$/.test(pin) && parts.length === 0) return null;

  const params = new URLSearchParams({
    format: 'json',
    limit: '1',
    countrycodes: 'in',
  });
  const query = [...parts, pin ? pin : null, 'India'].filter(Boolean).join(', ');
  params.set('q', query);
  if (/^\d{6}$/.test(pin)) params.set('postalcode', pin);

  const response = await fetchImpl(`https://nominatim.openstreetmap.org/search?${params.toString()}`, {
    headers: {
      Accept: 'application/json',
      'Accept-Language': 'en',
    },
  });
  if (!response.ok) return null;
  const data = await response.json();
  const first = Array.isArray(data) ? data[0] : null;
  return asGeoPoint({
    latitude: first?.lat,
    longitude: first?.lon,
  });
}

export async function enrichAddressWithCoordinates(
  address: ProfileAddress | AddressLike | undefined,
  options?: { force?: boolean; fetchImpl?: typeof fetch },
): Promise<ProfileAddress> {
  const current = { ...(address ?? {}) };
  const existing = asGeoPoint(current.coordinates);
  if (existing && !options?.force) {
    return { ...current, coordinates: existing };
  }
  const point = await geocodeIndiaAddress(current, options?.fetchImpl);
  if (!point) return current;
  return { ...current, coordinates: point };
}
