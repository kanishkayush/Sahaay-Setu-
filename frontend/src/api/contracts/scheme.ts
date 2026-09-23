import { z } from 'zod';
import { CitationSchema, LanguageCodeSchema, RupeesSchema } from './common';

/**
 * A concessional credit / education loan scheme routed through the
 * Channel Finance System (NSFDC-style).
 *
 * ⚠️  BACKEND CONTRACT FILE — see docs/API_CONTRACT.md
 */

export const OfficialCategorySchema = z.enum([
  'NGO',
  'EDUCATION',
  'ECONOMIC_DEVELOPMENT',
  'SOCIAL_EMPOWERMENT'
]);
export type OfficialCategory = z.infer<typeof OfficialCategorySchema>;

export const BeneficiaryGenderSchema = z.enum(['MALE', 'FEMALE', 'OTHER', 'ANY']);

/** Localised display strings, keyed by language. `en` is mandatory. */
export const LocalizedTextSchema = z
  .record(LanguageCodeSchema, z.string())
  .refine((v) => typeof v.en === 'string' && v.en.length > 0, {
    message: 'English (`en`) copy is required as the fallback',
  });
export type LocalizedText = z.infer<typeof LocalizedTextSchema>;

export const EligibilityRuleSchema = z.object({
  /** Machine-evaluable so the client can pre-filter offline. */
  field: z.enum([
    'annualFamilyIncome',
    'projectCost',
    'age',
    'gender',
    'caste',
    'educationStatus',
    'projectType',
    'isUrban',
  ]),
  operator: z.enum(['lte', 'gte', 'eq', 'in', 'between']),
  value: z.union([z.number(), z.string(), z.array(z.union([z.number(), z.string()]))]),
  /** Human explanation shown under "Why you qualify / don't qualify". */
  label: LocalizedTextSchema,
});
export type EligibilityRule = z.infer<typeof EligibilityRuleSchema>;

export const SchemeSchema = z.object({
  id: z.string(),
  code: z.string(), // e.g. "NSFDC-TL"
  name: LocalizedTextSchema,
  shortDescription: LocalizedTextSchema,
  officialCategory: OfficialCategorySchema,
  recommendationCategory: z.array(z.string()).default([]),

  /** Money & terms */
  minLoanAmount: RupeesSchema.optional(),
  maxLoanAmount: RupeesSchema.optional(),
  /** Share of project cost the scheme funds, 0–1. e.g. 0.9 = 90% */
  fundingSharePct: z.number().min(0).max(1).optional(),
  interestRateMinPct: z.number().min(0).max(30).optional(),
  interestRateMaxPct: z.number().min(0).max(30).optional(),
  /** Concessional rate specifically for women beneficiaries, if any. */
  womenInterestRatePct: z.number().min(0).max(30).optional(),
  maxTenureMonths: z.number().int().positive().optional(),
  moratoriumMinMonths: z.number().int().nonnegative().optional(),
  moratoriumMaxMonths: z.number().int().nonnegative().optional(),

  /** Eligibility */
  maxAnnualFamilyIncome: RupeesSchema.optional(),
  eligibleGender: BeneficiaryGenderSchema.default('ANY'),
  eligibilityRules: z.array(EligibilityRuleSchema).default([]),

  /** Presentation */
  documentsRequired: z.array(LocalizedTextSchema).default([]),
  /** Which Channel Partner types can process this scheme. */
  channelPartnerTypes: z.array(z.enum(['SCA', 'PSB', 'RRB', 'NBFC_MFI', 'COOP_BANK', 'SFB', 'UNKNOWN'])).default([]),
  channelPartnerRequired: z.boolean().default(false),
  officialUrl: z.union([z.string().url(), z.literal('')]).optional(),
  applicationUrl: z.union([z.string().url(), z.literal('')]).optional(),
  implementingOrganization: z.string().optional(),
  
  /** Verification Metadata */
  sourceUrl: z.union([z.string().url(), z.literal('')]).optional(),
  sourceName: z.string().optional(),
  lastVerified: z.string().optional(),
  verificationStatus: z.string().optional(),

  citations: z.array(CitationSchema).default([]),
  /** Set false when data is seeded/unverified — the UI shows a warning chip. */
  verified: z.boolean().default(false),
  lastUpdatedAt: z.string(), // ISO-8601
});
export type Scheme = z.infer<typeof SchemeSchema>;

export const SchemeListResponseSchema = z.object({
  items: z.array(SchemeSchema),
  /** Warning banner text when the catalogue is seed data, not official. */
  dataDisclaimer: LocalizedTextSchema.nullable().optional(),
});
export type SchemeListResponse = z.infer<typeof SchemeListResponseSchema>;
