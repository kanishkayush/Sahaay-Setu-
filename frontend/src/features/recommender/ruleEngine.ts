// @ts-nocheck
import type {
  ApplicantProfile,
  MatchReason,
  RecommendationResponse,
  Scheme,
  OfficialCategory,
  SchemeRecommendation,
} from '@/api/contracts';
import { eligibleLoanAmount, marginMoney } from '@/features/calculator/emi';

/**
 * Smart Scheme Recommender — deterministic, on-device rule engine.
 *
 * Two reasons this exists even though an AI backend is coming:
 *   1. OFFLINE FALLBACK. Poor connectivity is the norm for our users; the app
 *      must still recommend something useful with no network.
 *   2. EXPLAINABILITY BASELINE. Public money is involved, so every AI
 *      recommendation can be diffed against a rule-based answer. When the
 *      backend and this engine disagree, that is a signal worth surfacing.
 *
 * The backend's `POST /v1/recommendations` returns the SAME shape, ideally
 * `source: 'HYBRID'` — these rules for eligibility, RAG for the explanation.
 */

const CATEGORY_BY_PROJECT_TYPE: Record<string, OfficialCategory[]> = {
  AGRICULTURE: ['ECONOMIC_DEVELOPMENT'],
  ANIMAL_HUSBANDRY: ['ECONOMIC_DEVELOPMENT'],
  ARTISAN_CRAFT: ['ECONOMIC_DEVELOPMENT'],
  RETAIL_SHOP: ['ECONOMIC_DEVELOPMENT'],
  SERVICES: ['ECONOMIC_DEVELOPMENT'],
  SMALL_MANUFACTURING: ['ECONOMIC_DEVELOPMENT'],
  TRANSPORT_VEHICLE: ['ECONOMIC_DEVELOPMENT'],
  EDUCATION: ['EDUCATION'],
  OTHER: ['ECONOMIC_DEVELOPMENT'],
};

const EDUCATION_RANK: Record<string, number> = {
  NONE: 0,
  PRIMARY: 1,
  SECONDARY: 2,
  HIGHER_SECONDARY: 3,
  VOCATIONAL: 4,
  GRADUATE: 5,
  POSTGRADUATE: 6,
};

type Scored = {
  scheme: Scheme;
  score: number;
  reasons: MatchReason[];
  /** Non-empty → the applicant is NOT eligible; used to build "near misses". */
  blockers: MatchReason[];
};

function reason(kind: MatchReason['kind'], en: string, hi: string): MatchReason {
  return { kind, text: { en, hi } };
}

function formatInr(amount: number): string {
  return `₹${amount.toLocaleString('en-IN')}`;
}

/** Applies hard eligibility gates and accumulates a 0–100 fit score. */
function scoreScheme(scheme: Scheme, profile: ApplicantProfile): Scored {
  const reasons: MatchReason[] = [];
  const blockers: MatchReason[] = [];
  let score = 0;

  // ---- Hard gate 1: income ceiling -------------------------------------
  if (scheme.maxAnnualFamilyIncome !== undefined) {
    if (profile.annualFamilyIncome > scheme.maxAnnualFamilyIncome) {
      blockers.push(
        reason(
          'MISMATCH',
          `Annual family income must be under ${formatInr(scheme.maxAnnualFamilyIncome)}`,
          `वार्षिक पारिवारिक आय ${formatInr(scheme.maxAnnualFamilyIncome)} से कम होनी चाहिए`,
        ),
      );
    } else {
      score += 25;
      reasons.push(
        reason(
          'MATCH',
          `Your family income is within the ${formatInr(scheme.maxAnnualFamilyIncome)} ceiling`,
          `आपकी पारिवारिक आय ${formatInr(scheme.maxAnnualFamilyIncome)} की सीमा के भीतर है`,
        ),
      );
    }
  }

  // ---- Hard gate 2: gender-restricted schemes --------------------------
  if (scheme.eligibleGender !== 'ANY') {
    if (!profile.gender) {
      blockers.push(
        reason(
          'INFO',
          'This scheme is for women beneficiaries — tell us your gender to check',
          'यह योजना महिला लाभार्थियों के लिए है — जाँच हेतु अपना लिंग बताएं',
        ),
      );
    } else if (profile.gender !== scheme.eligibleGender) {
      blockers.push(
        reason('MISMATCH', 'Reserved for women beneficiaries', 'केवल महिला लाभार्थियों के लिए'),
      );
    } else {
      score += 15;
      reasons.push(
        reason(
          'MATCH',
          'Reserved for women — you get the lowest concessional rate',
          'महिलाओं के लिए आरक्षित — आपको न्यूनतम रियायती दर मिलेगी',
        ),
      );
    }
  }

  // ---- Hard gate 3: education schemes need an education project --------
  const isEducationScheme = scheme.officialCategory === 'EDUCATION';
  const wantsEducation = profile.projectType === 'EDUCATION';
  if (isEducationScheme !== wantsEducation) {
    blockers.push(
      isEducationScheme
        ? reason(
            'MISMATCH',
            'This is an education loan — choose "Education" as your purpose',
            'यह शिक्षा ऋण है — उद्देश्य में "शिक्षा" चुनें',
          )
        : reason(
            'MISMATCH',
            'This is a business loan, not for course fees',
            'यह व्यवसाय ऋण है, पाठ्यक्रम शुल्क के लिए नहीं',
          ),
    );
  }

  if (isEducationScheme && wantsEducation) {
    const rank = EDUCATION_RANK[profile.educationStatus] ?? 0;
    if (rank >= 3) {
      score += 20;
      reasons.push(
        reason(
          'MATCH',
          'Your education level qualifies for a professional/technical course loan',
          'आपका शैक्षिक स्तर व्यावसायिक/तकनीकी पाठ्यक्रम ऋण के लिए योग्य है',
        ),
      );
    } else {
      blockers.push(
        reason(
          'MISMATCH',
          'Needs at least higher-secondary completion',
          'कम से कम उच्चतर माध्यमिक उत्तीर्ण होना आवश्यक',
        ),
      );
    }
  }

  // ---- Soft signal: does the ticket size fit? --------------------------
  if (scheme.fundingSharePct !== undefined && scheme.maxLoanAmount !== undefined && scheme.minLoanAmount !== undefined) {
    const loan = eligibleLoanAmount(
      profile.estimatedProjectCost,
      scheme.fundingSharePct,
      scheme.maxLoanAmount,
    );

    if (loan < scheme.minLoanAmount) {
      blockers.push(
        reason(
          'MISMATCH',
          `Your project is too small — this scheme starts at ${formatInr(scheme.minLoanAmount)}`,
          `आपकी परियोजना बहुत छोटी है — यह योजना ${formatInr(scheme.minLoanAmount)} से शुरू होती है`,
        ),
      );
    } else {
      // Best score when the scheme covers the full 90% without hitting its cap.
      const uncapped = Math.floor(profile.estimatedProjectCost * scheme.fundingSharePct);
      const coverage = uncapped === 0 ? 0 : loan / uncapped;
      score += Math.round(30 * coverage);

      if (coverage >= 0.999) {
        const margin = marginMoney(profile.estimatedProjectCost, loan);
        const pct = Math.round(scheme.fundingSharePct * 100);
        reasons.push(
          reason(
            'MATCH',
            margin > 0
              ? `Funds ${pct}% of project cost — you arrange the remaining ${formatInr(margin)}`
              : `Covers ${pct}% of your project — ${formatInr(loan)}`,
            margin > 0
              ? `परियोजना लागत का ${pct}% वित्तपोषित — शेष ${formatInr(margin)} आपको जुटाने होंगे`
              : `आपकी परियोजना का ${pct}% कवर — ${formatInr(loan)}`,
          ),
        );
      } else {
        reasons.push(
          reason(
            'INFO',
            `Caps at ${formatInr(scheme.maxLoanAmount)}, so you would need to arrange the rest`,
            `अधिकतम ${formatInr(scheme.maxLoanAmount)} — शेष राशि की व्यवस्था स्वयं करनी होगी`,
          ),
        );
      }
    }
  }

  // ---- Soft signal: category matches the stated project type -----------
  const preferred = CATEGORY_BY_PROJECT_TYPE[profile.projectType] ?? [];
  const categoryIndex = preferred.indexOf(scheme.officialCategory);
  if (categoryIndex === 0) {
    score += 20;
    reasons.push(
      reason(
        'MATCH',
        'Designed exactly for this kind of activity',
        'ठीक इसी प्रकार की गतिविधि के लिए बनाई गई',
      ),
    );
  } else if (categoryIndex > 0) {
    score += 10;
  }

  // ---- Soft signal: cheaper money wins ---------------------------------
  // Weighted at 20, not 10. The verified catalogue spans 6.5% to 15% — an
  // Aajeevika micro-loan costs more than twice a Micro Finance one for the same
  // amount — so the rate is now the largest cost difference between two
  // otherwise similar schemes, and the ranking should say so.
  const rate = applicableRate(scheme, profile);
  if (rate !== undefined) {
    score += Math.round(Math.max(0, (15 - rate) / 15) * 20);
  }

  return { scheme, score: Math.min(100, score), reasons, blockers };
}

/** Women's concessional rate where the scheme offers one, else the floor rate. */
export function applicableRate(scheme: Scheme, profile: ApplicantProfile): number | undefined {
  if (profile.gender === 'FEMALE' && scheme.womenInterestRatePct !== undefined) {
    return scheme.womenInterestRatePct;
  }
  return scheme.interestRateMinPct;
}

function toRecommendation(scored: Scored, profile: ApplicantProfile): SchemeRecommendation {
  const { scheme } = scored;
  let loan = 0;
  if (scheme.fundingSharePct !== undefined && scheme.maxLoanAmount !== undefined) {
    loan = eligibleLoanAmount(
      profile.estimatedProjectCost,
      scheme.fundingSharePct,
      scheme.maxLoanAmount,
    );
  }

  return {
    scheme,
    score: scored.score,
    eligibleLoanAmount: loan,
    applicableInterestRatePct: applicableRate(scheme, profile),
    suggestedTenureMonths: scheme.maxTenureMonths ?? 0,
    suggestedMoratoriumMonths: scheme.moratoriumMinMonths ?? 0,
    reasons: [...scored.blockers, ...scored.reasons],
    citations: [],
    source: 'RULE_ENGINE',
  };
}

/**
 * Rank every scheme for an applicant.
 * Eligible schemes go to `recommendations`; the rest become `nearMisses` so the
 * user learns *why* they were excluded instead of just seeing a short list.
 */
export function recommendSchemes(
  schemes: Scheme[],
  profile: ApplicantProfile,
  limit = 5,
): RecommendationResponse {
  const scored = schemes.map((scheme) => scoreScheme(scheme, profile));

  const eligible = scored
    .filter((s) => s.blockers.length === 0)
    .sort((a, b) => b.score - a.score)
    .slice(0, limit)
    .map((s) => toRecommendation(s, profile));

  const nearMisses = scored
    .filter((s) => s.blockers.length > 0)
    .sort((a, b) => a.blockers.length - b.blockers.length || b.score - a.score)
    .slice(0, 3)
    .map((s) => toRecommendation(s, profile));

  return {
    recommendations: eligible,
    nearMisses,
    generatedAt: new Date().toISOString(),
    offline: true,
  };
}
