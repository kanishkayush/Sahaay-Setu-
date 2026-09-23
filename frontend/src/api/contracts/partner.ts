import { z } from 'zod';
import { GeoPointSchema, LanguageCodeSchema } from './common';
import { OfficialCategorySchema } from './scheme';

/**
 * Geo-Spatial Channel Partner Locator & Router.
 *
 * ⚠️  BACKEND CONTRACT FILE — see docs/API_CONTRACT.md
 *
 * The routing rule from the problem statement: never surface a partner whose
 * fund-utilisation health is poor (high NPA / overdues). That judgement lives on
 * the server; the client only renders `eligibility`.
 */

export const PartnerTypeSchema = z.enum(['SCA', 'PSB', 'RRB', 'NBFC_MFI', 'COOP_BANK', 'SFB', 'UNKNOWN']);
export type PartnerType = z.infer<typeof PartnerTypeSchema>;

/**
 * Whether this partner may currently receive new applications.
 *
 * Computed server-side against the norms for the partner's TYPE — they differ
 * per type and must not be collapsed into one threshold. See
 * src/features/partners/eligibilityNorms.ts, whose `requiredInputsFor()` lists
 * the fields a feed would have to supply; the three optional fields below are
 * the only ones this contract can carry today, and all three are absent.
 */
export const PartnerEligibilitySchema = z.object({
  /**
   * UNKNOWN is a first-class state, not a placeholder. NSFDC does not publish
   * per-partner NPA or fund-utilisation figures, so for most partners this is
   * the honest answer until a data feed exists. The client must not present an
   * UNKNOWN partner as accepting.
   */
  status: z.enum(['ACCEPTING', 'LIMITED', 'NOT_ACCEPTING', 'UNKNOWN']),
  /** i18n key, e.g. 'partners.eligibility.highNpa' */
  reasonKey: z.string(),
  npaPct: z.number().min(0).max(100).optional(),
  overdueAmount: z.number().nonnegative().optional(),
  unutilisedLimit: z.number().nonnegative().optional(),
  lastAssessedAt: z.string().optional(),
});
export type PartnerEligibility = z.infer<typeof PartnerEligibilitySchema>;

export const ChannelPartnerSchema = z.object({
  id: z.string(),
  name: z.string(),
  /** Transliterated / translated names for display in the chosen language. */
  localizedNames: z.record(LanguageCodeSchema, z.string()).optional(),
  type: PartnerTypeSchema,
  branchName: z.string().optional(),
  address: z.string(),
  district: z.string(),
  stateCode: z.string().length(2),
  pincode: z.string(),
  location: GeoPointSchema.optional(),
  phone: z.string().optional(),
  email: z.string().email().optional(),
  /** Which scheme categories this branch is authorised to process. */
  supportedSchemeCategories: z.array(OfficialCategorySchema),
  supportedSchemeIds: z.array(z.string()).default([]),
  schemeMatch: z.boolean().default(true),
  schemeMappingStatus: z.string().default('VERIFIED_FOR_SELECTED_SCHEME'),
  eligibility: PartnerEligibilitySchema,
  /** Straight-line km from the requested point; server-computed. */
  distanceKm: z.number().nonnegative().optional(),
  languagesSpoken: z.array(LanguageCodeSchema).default([]),
  lastUpdatedAt: z.string(),
});
export type ChannelPartner = z.infer<typeof ChannelPartnerSchema>;

export const PartnerSearchRequestSchema = z.object({
  location: GeoPointSchema.optional(),
  pincode: z.string().optional(),
  radiusKm: z.number().min(1).max(1000).default(25),
  schemeId: z.string().optional(),
  schemeCategory: OfficialCategorySchema.optional(),
  partnerTypes: z.array(PartnerTypeSchema).optional(),
  /**
   * Hide partners that cannot disburse. Default true — this is the whole point.
   * UNKNOWN partners are still shown: we cannot assert they are unavailable
   * either, and the UI tells the user to call ahead.
   */
  onlyAccepting: z.boolean().default(true),
  language: LanguageCodeSchema.optional(),
  /** When true, returns the complete partner dataset regardless of geography. */
  allPartners: z.boolean().default(false),
});
export type PartnerSearchRequest = z.infer<typeof PartnerSearchRequestSchema>;

export const PartnerSearchResponseSchema = z.object({
  items: z.array(ChannelPartnerSchema),
  /** Set when every nearby partner was filtered out for poor fund health. */
  fallbackUsed: z.boolean().default(false),
  searchedFrom: GeoPointSchema.optional(),
  radiusKm: z.number(),
});
export type PartnerSearchResponse = z.infer<typeof PartnerSearchResponseSchema>;
