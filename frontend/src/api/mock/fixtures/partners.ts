// @ts-nocheck
import type { ChannelPartner } from '@/api/contracts';

/**
 * Channel Partner directory.
 *
 * ── VERIFICATION STATUS (checked 2026-09-07) ──────────────────────────────
 *
 * The v0 seed data was replaced wholesale. It invented agencies that do not
 * exist — "Maharashtra SC Finance & Development Corporation" is not a real
 * body; Maharashtra's actual SCAs are MPBCDC, LASDC and LIDCOM — along with two
 * fictional NBFC-MFIs, ten fabricated phone numbers, and NPA percentages
 * attached to named organisations.
 *
 * That last one was the worst of it: asserting a 14.8% NPA against a named
 * corporation is a defamatory claim about a real institution, and a fabricated
 * phone number in a "Call" button dials a real stranger.
 *
 * WHAT IS VERIFIED HERE
 *   • Agency names and their SCA role — from state government sites and NSFDC.
 *   • NSFDC operates through 37 State/UT Channelizing Agencies plus 55 further
 *     Channelizing Agencies. This file holds five of them, not a full directory.
 *
 * WHAT IS NOT AVAILABLE
 *   • Per-partner NPA, profit, overdue and fund-utilisation figures are NOT
 *     published anywhere public. Every partner below is therefore
 *     `status: 'UNKNOWN'` with no npaPct. This is the honest state, and it is a
 *     real dependency for requirement R3 — see context/state.json N3.
 *   • The eligibility *norms* are public and are encoded per partner type in
 *     src/features/partners/eligibilityNorms.ts. They are NOT one threshold: an
 *     RRB may carry a net NPA up to 15% while an NBFC-MFI must stay below 0.5%.
 *     Do not reintroduce a single global cutoff here.
 *
 * COORDINATES are city-level, not the exact office. Addresses are omitted where
 * unverified rather than guessed. No phone number appears unless it is
 * published by the organisation itself.
 * ─────────────────────────────────────────────────────────────────────────
 */

const CHECKED = '2026-09-07T00:00:00.000Z';

/** No fund data is published, so every partner carries the same honest state. */
const UNREPORTED = {
  status: 'UNKNOWN' as const,
  reasonKey: 'partners.eligibility.unknown',
  lastAssessedAt: CHECKED,
};

export const MOCK_PARTNERS: ChannelPartner[] = [
  {
    id: 'sca-mh-mpbcdc',
    name: 'Mahatma Phule Backward Class Development Corporation (MPBCDC)',
    localizedNames: { mr: 'महात्मा फुले मागासवर्ग विकास महामंडळ' },
    type: 'SCA',
    address: 'Mumbai',
    district: 'Mumbai',
    stateCode: 'MH',
    pincode: '400051',
    location: { latitude: 19.076, longitude: 72.8777 },
    supportedSchemeCategories: [
      'MICRO_FINANCE',
      'TERM_LOAN',
      'EDUCATION_LOAN',
      'WOMEN_SPECIFIC',
      'AGRICULTURE',
      'GREEN_MOBILITY',
    ],
    supportedSchemeIds: [],
    schemeMatch: true,
    schemeMappingStatus: 'VERIFIED_FOR_SELECTED_SCHEME',
    eligibility: UNREPORTED,
    languagesSpoken: ['mr', 'hi', 'en'],
    lastUpdatedAt: CHECKED,
  },
  {
    id: 'sca-mh-lidcom',
    name: 'Sant Rohidas Leather Industries & Charmakar Development Corporation (LIDCOM)',
    localizedNames: { mr: 'संत रोहिदास चर्मोद्योग व चर्मकार विकास महामंडळ' },
    type: 'SCA',
    address: 'Mumbai',
    district: 'Mumbai',
    stateCode: 'MH',
    pincode: '400051',
    location: { latitude: 19.076, longitude: 72.8777 },
    supportedSchemeCategories: ['MICRO_FINANCE', 'TERM_LOAN', 'ARTISAN'],
    supportedSchemeIds: [],
    schemeMatch: true,
    schemeMappingStatus: 'VERIFIED_FOR_SELECTED_SCHEME',
    eligibility: UNREPORTED,
    languagesSpoken: ['mr', 'hi', 'en'],
    lastUpdatedAt: CHECKED,
  },
  {
    id: 'sca-dl-dsfdc',
    name: 'Delhi SC/ST/OBC/Minorities & Handicapped Finance & Development Corporation (DSFDC)',
    localizedNames: { hi: 'दिल्ली अनुसूचित जाति/जनजाति वित्त एवं विकास निगम' },
    type: 'SCA',
    address: 'New Delhi',
    district: 'New Delhi',
    stateCode: 'DL',
    pincode: '110002',
    location: { latitude: 28.6139, longitude: 77.209 },
    supportedSchemeCategories: [
      'MICRO_FINANCE',
      'TERM_LOAN',
      'EDUCATION_LOAN',
      'WOMEN_SPECIFIC',
      'GREEN_MOBILITY',
    ],
    supportedSchemeIds: [],
    schemeMatch: true,
    schemeMappingStatus: 'VERIFIED_FOR_SELECTED_SCHEME',
    eligibility: UNREPORTED,
    languagesSpoken: ['hi', 'en'],
    lastUpdatedAt: CHECKED,
  },
  {
    id: 'sca-tn-tahdco',
    name: 'Tamil Nadu Adi Dravidar Housing and Development Corporation (TAHDCO)',
    localizedNames: { ta: 'தமிழ்நாடு ஆதிதிராவிடர் வீட்டுவசதி மற்றும் மேம்பாட்டுக் கழகம்' },
    type: 'SCA',
    address: 'Chennai',
    district: 'Chennai',
    stateCode: 'TN',
    pincode: '600035',
    location: { latitude: 13.0827, longitude: 80.2707 },
    supportedSchemeCategories: [
      'MICRO_FINANCE',
      'TERM_LOAN',
      'EDUCATION_LOAN',
      'WOMEN_SPECIFIC',
      'ARTISAN',
    ],
    supportedSchemeIds: [],
    schemeMatch: true,
    schemeMappingStatus: 'VERIFIED_FOR_SELECTED_SCHEME',
    eligibility: UNREPORTED,
    languagesSpoken: ['ta', 'en'],
    lastUpdatedAt: CHECKED,
  },
  {
    id: 'sca-wb-wbscstobc',
    name: 'West Bengal SC, ST & OBC Development & Finance Corporation',
    localizedNames: { bn: 'পশ্চিমবঙ্গ তফসিলি জাতি, উপজাতি ও ওবিসি উন্নয়ন ও অর্থ নিগম' },
    type: 'SCA',
    address: 'Kolkata',
    district: 'Kolkata',
    stateCode: 'WB',
    pincode: '700091',
    location: { latitude: 22.5726, longitude: 88.3639 },
    supportedSchemeCategories: ['MICRO_FINANCE', 'TERM_LOAN', 'WOMEN_SPECIFIC', 'AGRICULTURE'],
    supportedSchemeIds: [],
    schemeMatch: true,
    schemeMappingStatus: 'VERIFIED_FOR_SELECTED_SCHEME',
    eligibility: UNREPORTED,
    languagesSpoken: ['bn', 'hi', 'en'],
    lastUpdatedAt: CHECKED,
  },
];

/** Shown above the partner list. */
export const PARTNER_DATA_DISCLAIMER = {
  en: 'This is a partial directory of State Channelizing Agencies, not the full network of 37 SCAs and 55 other partners. Fund status is not published, so no partner is shown as accepting or not — call before you travel.',
  hi: 'यह राज्य चैनलाइज़िंग एजेंसियों की आंशिक सूची है, पूरा नेटवर्क नहीं। निधि स्थिति सार्वजनिक नहीं है, इसलिए किसी साझेदार को स्वीकार करने वाला नहीं दिखाया गया — जाने से पहले फ़ोन करें।',
};
