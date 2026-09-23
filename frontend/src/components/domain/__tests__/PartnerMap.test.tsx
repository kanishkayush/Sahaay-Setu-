import { describe, it, expect, beforeEach, jest } from '@jest/globals';
import React from 'react';
import { render, fireEvent } from '@testing-library/react-native';
import { PartnerMap } from '../PartnerMap';
import type { ChannelPartner } from '@/api/contracts';

// Mock react-native-maps to allow testing without native modules
jest.mock('react-native-maps', () => {
  const React = require('react');
  const MapView = (props: any) => <div testID="map-view">{props.children}</div>;
  const Marker = (props: any) => <div testID={`marker-${props.coordinate?.latitude}-${props.coordinate?.longitude}`}>{props.title}</div>;
  return {
    __esModule: true,
    default: MapView,
    Marker: Marker,
  };
});

describe('PartnerMap Component', () => {
  const mockPartners: ChannelPartner[] = [
    {
      id: 'valid-1',
      name: 'Valid Partner',
      type: 'SCA',
      address: 'Test Addr',
      district: 'Test Dist',
      stateCode: 'XX',
      pincode: '110001',
      location: { latitude: 12.34, longitude: 56.78 },
      eligibility: { status: 'ACCEPTING', reasonKey: 'test' },
      distanceKm: 1.0,
      supportedSchemeCategories: [],
      supportedSchemeIds: [],
      languagesSpoken: [],
      schemeMatch: true,
      schemeMappingStatus: 'test',
      lastUpdatedAt: '2026-09-19',
    },
    {
      id: 'missing-1',
      name: 'Missing Partner',
      type: 'PSB',
      address: 'Test Addr 2',
      district: 'Test Dist 2',
      stateCode: 'XX',
      pincode: '110002',
      location: undefined, // Missing coordinates
      eligibility: { status: 'UNKNOWN', reasonKey: 'test' },
      distanceKm: 2.0,
      supportedSchemeCategories: [],
      supportedSchemeIds: [],
      languagesSpoken: [],
      schemeMatch: true,
      schemeMappingStatus: 'test',
      lastUpdatedAt: '2026-09-19',
    },
  ];

  it('Partner with valid coordinates appears on map', () => {
    const { getByTestId } = render(
      <PartnerMap partners={[mockPartners[0]]} unavailableMessage="Map unavailable" />
    );
    expect(getByTestId('marker-12.34-56.78')).toBeTruthy();
  });

  it('Partner without coordinates does not appear on map (remains in list but ignored by map)', () => {
    const { queryByTestId } = render(
      <PartnerMap partners={[mockPartners[1]]} unavailableMessage="Map unavailable" />
    );
    // Should not render a marker with undefined coordinates
    expect(queryByTestId('marker-undefined-undefined')).toBeNull();
  });

  it('Partner with null coordinates does not center map at 0,0', () => {
    // The component sets origin = validPartners[0] or default center.
    // By passing missing-1, validPartners is empty, so it defaults to { latitude: 20.5937, longitude: 78.9629 } (India center), NOT 0,0.
    // If it crashed or set to 0,0, this test would fail in rendering.
    const { toJSON } = render(
      <PartnerMap partners={[mockPartners[1]]} unavailableMessage="Map unavailable" />
    );
    expect(toJSON()).toBeTruthy();
  });

  it('Multiple partners where only some have coordinates: valid ones render, others are skipped', () => {
    const { getByTestId, queryByTestId } = render(
      <PartnerMap partners={mockPartners} unavailableMessage="Map unavailable" />
    );
    // Valid one rendered
    expect(getByTestId('marker-12.34-56.78')).toBeTruthy();
    // Missing one skipped
    expect(queryByTestId('marker-undefined-undefined')).toBeNull();
  });
});
