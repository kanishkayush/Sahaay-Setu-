import * as ExpoLocation from 'expo-location';
import { useCallback, useState } from 'react';
import { Platform } from 'react-native';
import type { GeoPoint } from '@/api/contracts';

type LocationState = {
  point: GeoPoint | null;
  addressData: ExpoLocation.LocationGeocodedAddress | null;
  status: 'idle' | 'requesting' | 'granted' | 'denied' | 'error';
  error: string | null;
};

/**
 * Validates GPS coordinates are real numbers and not the 0,0 null-island default.
 */
function isValidCoordinate(lat: unknown, lon: unknown): boolean {
  if (typeof lat !== 'number' || typeof lon !== 'number') return false;
  if (!Number.isFinite(lat) || !Number.isFinite(lon)) return false;
  // Reject 0,0 — it's null island, never a real user location
  if (lat === 0 && lon === 0) return false;
  return true;
}

/**
 * Browser geolocation fallback for Expo Web.
 * Returns a Promise that resolves to { latitude, longitude } or rejects.
 */
function getBrowserPosition(): Promise<{ latitude: number; longitude: number }> {
  return new Promise((resolve, reject) => {
    if (typeof navigator === 'undefined' || !navigator.geolocation) {
      reject(new Error('Browser geolocation not available'));
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (pos) => resolve({ latitude: pos.coords.latitude, longitude: pos.coords.longitude }),
      (err) => {
        switch (err.code) {
          case err.PERMISSION_DENIED:
            reject(new Error('PERMISSION_DENIED'));
            break;
          case err.POSITION_UNAVAILABLE:
            reject(new Error('POSITION_UNAVAILABLE'));
            break;
          case err.TIMEOUT:
            reject(new Error('TIMEOUT'));
            break;
          default:
            reject(new Error(err.message || 'Unknown geolocation error'));
        }
      },
      { enableHighAccuracy: false, timeout: 15000, maximumAge: 60000 },
    );
  });
}

/**
 * Browser reverse geocoding fallback for Expo Web using Nominatim API.
 */
async function getBrowserReverseGeocode(lat: number, lon: number): Promise<ExpoLocation.LocationGeocodedAddress | null> {
  try {
    const response = await fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lon}`);
    if (!response.ok) return null;
    const data = await response.json();
    if (!data || !data.address) return null;
    
    return {
      postalCode: data.address.postcode || null,
      subregion: data.address.county || data.address.city_district || data.address.state_district || null,
      region: data.address.state || null,
      city: data.address.city || data.address.town || data.address.village || null,
      country: data.address.country || null,
      district: data.address.suburb || null,
      isoCountryCode: data.address.country_code?.toUpperCase() || null,
      name: data.display_name || null,
      street: data.address.road || null,
      streetNumber: data.address.house_number || null,
      timezone: null,
      formattedAddress: data.display_name || null,
    };
  } catch (err) {
    console.error('[LOCATION] Browser reverse geocoding error:', err);
    return null;
  }
}

/**
 * Location is strictly opt-in and requested only when the user taps
 * "Use my location". We never ask on app start — a permission prompt with no
 * context is the fastest way to lose a first-time user's trust.
 *
 * This hook is local component state. The canonical location for Partners
 * comes from the backend profile (address.coordinates), NOT from this hook.
 */
export function useLocation() {
  const [state, setState] = useState<LocationState>({
    point: null,
    addressData: null,
    status: 'idle',
    error: null,
  } as any);

  const request = useCallback(async () => {
    console.log('[LOCATION] request started');
    setState((s) => ({ ...s, status: 'requesting', error: null }));

    try {
      let latitude: number;
      let longitude: number;

      if (Platform.OS === 'web') {
        // ─── Web path: use browser geolocation ───
        console.log('[LOCATION] Platform=web, using browser geolocation');
        try {
          const pos = await getBrowserPosition();
          latitude = pos.latitude;
          longitude = pos.longitude;
          console.log(`[LOCATION] browser GPS latitude=${latitude} longitude=${longitude}`);
        } catch (webErr) {
          const msg = webErr instanceof Error ? webErr.message : 'Unknown';
          console.error('[LOCATION] browser geolocation failed:', msg);
          if (msg === 'PERMISSION_DENIED') {
            setState({ point: null, addressData: null, status: 'denied', error: null } as any);
            return null;
          }
          setState({ point: null, addressData: null, status: 'error', error: msg } as any);
          return null;
        }
      } else {
        // ─── Native path: use Expo Location ───
        console.log('[LOCATION] Platform=native, using Expo Location');
        console.log('[LOCATION] requesting foreground permission...');
        const { status } = await ExpoLocation.requestForegroundPermissionsAsync();
        console.log(`[LOCATION] permission status=${status}`);

        if (status !== 'granted') {
          console.log('[LOCATION] permission denied');
          setState({ point: null, addressData: null, status: 'denied', error: null } as any);
          return null;
        }

        console.log('[LOCATION] requesting GPS coordinates...');
        const position = await ExpoLocation.getCurrentPositionAsync({
          accuracy: ExpoLocation.Accuracy.Balanced,
        });
        latitude = position.coords.latitude;
        longitude = position.coords.longitude;
        console.log(`[LOCATION] native GPS latitude=${latitude} longitude=${longitude}`);
      }

      // ─── Validate coordinates ───
      if (!isValidCoordinate(latitude, longitude)) {
        console.error(`[LOCATION] invalid coordinates: lat=${latitude}, lon=${longitude}`);
        setState({ point: null, addressData: null, status: 'error', error: 'Invalid coordinates received' } as any);
        return null;
      }

      const point: GeoPoint = { latitude, longitude };
      console.log('[LOCATION] GPS coordinates validated:', JSON.stringify(point));

      // ─── Reverse geocode ───
      let addressData: ExpoLocation.LocationGeocodedAddress | null = null;
      try {
        console.log('[LOCATION] requesting reverse geocode...');
        if (Platform.OS === 'web') {
          console.log('[LOCATION] using browser reverse geocode fallback (Nominatim)');
          addressData = await getBrowserReverseGeocode(point.latitude, point.longitude);
        } else {
          const reverse = await ExpoLocation.reverseGeocodeAsync({
            latitude: point.latitude,
            longitude: point.longitude,
          });
          if (reverse && reverse.length > 0 && reverse[0]) {
            addressData = reverse[0];
          }
        }
        
        if (addressData) {
          console.log('[LOCATION] reverse geocode result:', JSON.stringify(addressData));
          console.log(`[LOCATION] postalCode=${addressData.postalCode}`);
          console.log(`[LOCATION] district=${addressData.subregion}`);
          console.log(`[LOCATION] state=${addressData.region}`);
        } else {
          console.warn('[LOCATION] reverse geocode returned empty results');
        }
      } catch (e) {
        console.error('[LOCATION] reverse geocoding failed:', e);
        // Coordinates are still valid — we just couldn't extract address fields
      }

      setState({ point, addressData, status: 'granted', error: null } as any);
      return { point, addressData };
    } catch (error) {
      const msg = error instanceof Error ? error.message : 'Unknown error';
      console.error('[LOCATION] GPS acquisition failed:', msg);
      setState({
        point: null,
        addressData: null,
        status: 'error',
        error: msg,
      } as any);
      return null;
    }
  }, []);

  return { ...state, request };
}
