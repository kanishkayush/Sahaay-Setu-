import { z } from 'zod';

const SchemeCategorySchema = z.enum([
  'MICRO_FINANCE', 'TERM_LOAN', 'EDUCATION_LOAN',
  'WOMEN_SPECIFIC', 'ARTISAN', 'AGRICULTURE', 'GREEN_MOBILITY',
]);

const LocalizedTextSchema = z.record(z.string(), z.string())
  .refine((v) => typeof v.en === 'string' && v.en.length > 0);

const EligibilityRuleSchema = z.object({
  field: z.enum(['annualFamilyIncome', 'projectCost', 'age', 'gender', 'caste', 'educationStatus', 'projectType', 'isUrban']),
  operator: z.enum(['lte', 'gte', 'eq', 'in', 'between']),
  value: z.any(),
  label: LocalizedTextSchema,
});

const CitationSchema = z.object({
  id: z.string(),
  title: z.string(),
  locator: z.string().optional(),
  url: z.string().url().optional(),
  confidence: z.number().min(0).max(1).optional(),
});

const SchemeSchema = z.object({
  id: z.string(),
  code: z.string(),
  name: LocalizedTextSchema,
  shortDescription: LocalizedTextSchema,
  category: SchemeCategorySchema,
  minLoanAmount: z.number().min(0),
  maxLoanAmount: z.number().min(0),
  fundingSharePct: z.number().min(0).max(1),
  interestRateMinPct: z.number().min(0).max(30),
  interestRateMaxPct: z.number().min(0).max(30),
  womenInterestRatePct: z.number().min(0).max(30).optional(),
  maxTenureMonths: z.number().int().positive(),
  moratoriumMinMonths: z.number().int().nonnegative(),
  moratoriumMaxMonths: z.number().int().nonnegative(),
  maxAnnualFamilyIncome: z.number().min(0),
  eligibleGender: z.enum(['MALE', 'FEMALE', 'OTHER', 'ANY']).default('ANY'),
  eligibilityRules: z.array(EligibilityRuleSchema).default([]),
  documentsRequired: z.array(LocalizedTextSchema).default([]),
  channelPartnerTypes: z.array(z.enum(['SCA', 'PSB', 'RRB', 'NBFC_MFI'])),
  officialUrl: z.string().url().optional(),
  sourceUrl: z.string().url().optional(),
  sourceName: z.string().optional(),
  lastVerified: z.string().optional(),
  verificationStatus: z.string().optional(),
  citations: z.array(CitationSchema).default([]),
  verified: z.boolean().default(false),
  lastUpdatedAt: z.string(),
});

const SchemeListResponseSchema = z.object({
  items: z.array(SchemeSchema),
  dataDisclaimer: LocalizedTextSchema.nullable().optional(),
});

async function test() {
  const res = await fetch('http://localhost:8000/v1/schemes');
  const data = await res.json();
  const parsed = SchemeListResponseSchema.safeParse(data);
  if (!parsed.success) {
    console.error(JSON.stringify(parsed.error.issues, null, 2));
  } else {
    console.log(`Success! Parsed ${parsed.data.items.length} schemes.`);
    console.log("Categories returned:", [...new Set(parsed.data.items.map(i => i.category))]);
  }
}
test();
