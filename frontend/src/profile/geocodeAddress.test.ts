import { describe, expect, it, vi } from 'vitest';
import { enrichAddressWithCoordinates, geocodeIndiaAddress } from './geocodeAddress';

describe('geocodeIndiaAddress', () => {
  it('returns null when the address has no PIN or place text', async () => {
    await expect(geocodeIndiaAddress({})).resolves.toBeNull();
  });

  it('forwards the saved PIN to Nominatim and normalizes the point', async () => {
    const fetchImpl = vi.fn(async () => ({
      ok: true,
      json: async () => [{ lat: '26.9124', lon: '75.7873' }],
    })) as unknown as typeof fetch;
    const point = await geocodeIndiaAddress({ pinCode: '302017', city: 'Jaipur', state: 'Rajasthan' }, fetchImpl);
    expect(point).toEqual({ latitude: 26.9124, longitude: 75.7873 });
    expect(String(fetchImpl.mock.calls[0]?.[0])).toContain('postalcode=302017');
    expect(String(fetchImpl.mock.calls[0]?.[0])).not.toContain('Jaipur=hardcoded');
  });
});

describe('enrichAddressWithCoordinates', () => {
  it('keeps existing valid coordinates without calling the geocoder', async () => {
    const fetchImpl = vi.fn() as unknown as typeof fetch;
    const address = await enrichAddressWithCoordinates(
      { pinCode: '302017', coordinates: { latitude: 26.9, longitude: 75.8 } },
      { fetchImpl },
    );
    expect(address.coordinates).toEqual({ latitude: 26.9, longitude: 75.8 });
    expect(fetchImpl).not.toHaveBeenCalled();
  });

  it('adds coordinates when a PIN is saved without a point', async () => {
    const fetchImpl = vi.fn(async () => ({
      ok: true,
      json: async () => [{ lat: '26.9124', lon: '75.7873' }],
    })) as unknown as typeof fetch;
    const address = await enrichAddressWithCoordinates(
      { pinCode: '302017', city: 'Jaipur', state: 'Rajasthan' },
      { fetchImpl },
    );
    expect(address.coordinates).toEqual({ latitude: 26.9124, longitude: 75.7873 });
  });
});
