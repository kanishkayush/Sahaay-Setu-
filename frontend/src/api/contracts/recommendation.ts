import { z } from 'zod';
import { CitationSchema, LanguageCodeSchema, RupeesSchema } from './common';
import { LocalizedTextSchema, SchemeSchema } from './scheme';

/**
 * Smart Scheme Recommender — request/response contract.
 *
 * ⚠️  BACKEND CONTRACT FILE — see docs/API_CONTRACT.md
 *
 * The client can answer this locally with the rule engine in
 * `src/features/recommender/ruleEngine.ts` (offline fallback). When the backend
 * is live, the same shape comes back from POST /v1/recommendations, ideally
 * enriched with RAG-grounded `reasoning` + `citations`.
 */

export const EducationStatusSchema = z.enum([
  'NONE',
  'PRIMARY',
  'SECONDARY',
  'HIGHER_SECONDARY',
  'GRADUATE',
  'POSTGRADUATE',
  'VOCATIONAL',
]);
export type EducationStatus = z.infer<typeof EducationStatusSchema>;

export const ProjectTypeSchema = z.enum([
  'AGRICULTURE',
  'ANIMAL_HUSBANDRY',
  'ARTISAN_CRAFT',
  'RETAIL_SHOP',
  'SERVICES',
  'SMALL_MANUFACTURING',
  'TRANSPORT_VEHICLE',
  'EDUCATION',
  'OTHER',
]);
export type ProjectType = z.infer<typeof ProjectTypeSchema>;

/** The five inputs the problem statement asks for, plus optional refinements. */
export const ApplicantProfileSchema = z.object({
  projectType: ProjectTypeSchema,
  estimatedProjectCost: RupeesSchema,
  annualFamilyIncome: RupeesSchema,
  educationStatus: EducationStatusSchema,
  gender: z.enum(['MALE', 'FEMALE', 'OTHER']).optional(),
  age: z.number().int().min(16).max(100).optional(),
  isUrban: z.boolean().optional(),
  stateCode: z.string().length(2).optional(), // ISO 3166-2:IN suffix, e.g. "MH"
  districtCode: z.string().optional(),
  /** Free-text, possibly in the user's own language — for the RAG layer. */
  narrative: z.string().max(1000).optional(),
});
export type ApplicantProfile = z.infer<typeof ApplicantProfileSchema>;

export const RecommendationRequestSchema = z.object({
  profile: ApplicantProfileSchema,
  language: LanguageCodeSchema,
  /** Cap results; default 5. */
  limit: z.number().int().min(1).max(20).optional(),
});
export type RecommendationRequest = z.infer<typeof RecommendationRequestSchema>;

export const MatchReasonSchema = z.object({
  kind: z.enum(['MATCH', 'MISMATCH', 'INFO']),
  text: LocalizedTextSchema,
});
export type MatchReason = z.infer<typeof MatchReasonSchema>;

export const SchemeRecommendationSchema = z.object({
  scheme: SchemeSchema,
  /** 0–100. Sorted descending by the server. */
  score: z.number().min(0).max(100),
  /** Loan the applicant would realistically get under this scheme. */
  eligibleLoanAmount: RupeesSchema,
  /** Rate actually applicable to *this* applicant (may use the women's rate). */
  applicableInterestRatePct: z.number().min(0).max(30),
  suggestedTenureMonths: z.number().int().nonnegative().optional(),
  suggestedMoratoriumMonths: z.number().int().nonnegative().optional(),
  /** Bulleted explanation shown in the "Why this scheme?" card. */
  reasons: z.array(MatchReasonSchema),
  /** Present only when the answer came from the RAG pipeline. */
  citations: z.array(CitationSchema).default([]),
  /** 'RULE_ENGINE' when computed on-device, 'AI' when the backend answered. */
  source: z.enum(['RULE_ENGINE', 'AI', 'HYBRID']),
});
export type SchemeRecommendation = z.infer<typeof SchemeRecommendationSchema>;

export const RecommendationResponseSchema = z.object({
  recommendations: z.array(SchemeRecommendationSchema),
  /** Schemes the applicant narrowly missed, with the blocking reason. */
  nearMisses: z.array(SchemeRecommendationSchema).default([]),
  generatedAt: z.string(),
  /** True when produced fully on-device because the network was unavailable. */
  offline: z.boolean().default(false),
});
export type RecommendationResponse = z.infer<typeof RecommendationResponseSchema>;
