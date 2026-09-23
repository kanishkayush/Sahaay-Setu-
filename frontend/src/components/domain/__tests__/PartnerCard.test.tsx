import { describe, it, expect, beforeEach, jest } from '@jest/globals';
import React from 'react';
import { render, fireEvent } from '@testing-library/react-native';
import { Linking } from 'react-native';
import { PartnerCard } from '../PartnerCard';

jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}));

const mockPartner = {
  id: 'partner-1',
  name: 'Test Partner',
  type: 'PSB' as const,
  address: '123 Main St',
  district: 'Test Dist',
  stateCode: 'TS',
  pincode: '123456',
  supportedSchemeCategories: [],
  eligibility: {
    status: 'ACCEPTING' as const,
    reasonKey: 'partners.eligibility.unknown',
  },
};

describe('PartnerCard', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    jest.spyOn(Linking, 'openURL').mockResolvedValue(true);
  });

  it('renders normally with valid location', () => {
    const partner = {
      ...mockPartner,
      location: { latitude: 20, longitude: 70 },
    };
    const { getByText } = render(<PartnerCard partner={partner} language="en" />);
    expect(getByText('Test Partner')).toBeTruthy();
    expect(getByText('partners.directions')).toBeTruthy();
  });

  it('opens directions with valid location', () => {
    const partner = {
      ...mockPartner,
      location: { latitude: 20, longitude: 70 },
    };
    const { getByText } = render(<PartnerCard partner={partner} language="en" />);
    const btn = getByText('partners.directions');
    fireEvent.press(btn);
    expect(Linking.openURL).toHaveBeenCalled();
  });

  it('renders normally with location=null', () => {
    const partner = {
      ...mockPartner,
      location: null as any,
    };
    const { getByText } = render(<PartnerCard partner={partner} language="en" />);
    expect(getByText('Test Partner')).toBeTruthy();
    expect(getByText('partners.locationUnavailable')).toBeTruthy();
  });

  it('renders normally with location=undefined', () => {
    const partner = {
      ...mockPartner,
      location: undefined,
    };
    const { getByText } = render(<PartnerCard partner={partner} language="en" />);
    expect(getByText('Test Partner')).toBeTruthy();
    expect(getByText('partners.locationUnavailable')).toBeTruthy();
  });

  it('does not crash when rendered without location', () => {
    const { getByText } = render(<PartnerCard partner={mockPartner} language="en" />);
    expect(getByText('Test Partner')).toBeTruthy();
  });

  it('does not attempt to open directions when location is unavailable', () => {
    const { getByText } = render(<PartnerCard partner={mockPartner} language="en" />);
    const btn = getByText('partners.locationUnavailable');
    fireEvent.press(btn);
    expect(Linking.openURL).not.toHaveBeenCalled();
  });
});
