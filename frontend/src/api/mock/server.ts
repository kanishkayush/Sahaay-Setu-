import type {
  AssistantQueryRequest,
  AssistantQueryResponse,
  ChannelPartner,
  PartnerSearchRequest,
  PartnerSearchResponse,
  RecommendationRequest,
  RecommendationResponse,
  Scheme,
  SchemeListResponse,
} from '@/api/contracts';
import { MOCK_LATENCY_MS } from '@/api/config';
import { MOCK_PARTNERS } from './fixtures/partners';
import { MOCK_SCHEMES, SCHEME_DATA_DISCLAIMER } from './fixtures/schemes';
import { answerFromKnowledgeBase } from './fixtures/assistant';
import { recommendSchemes } from '@/features/recommender/ruleEngine';
import { haversineKm } from '@/utils/geo';

/**
 * In-memory mock backend.
 *
 * Purpose: the frontend is fully demoable and testable with NO backend running,
 * so UI work is never blocked on the AI/RAG teammate. Every function here
 * mirrors one endpoint in `ENDPOINTS` and returns the exact contract shape.
 *
 * When the real backend lands, set EXPO_PUBLIC_USE_MOCK_API=false. Nothing else
 * in the app changes.
 */

const delay = (ms = MOCK_LATENCY_MS) => new Promise<void>((r) => setTimeout(r, ms));

export async function mockListSchemes(): Promise<SchemeListResponse> {
  await delay();
  return { items: MOCK_SCHEMES, dataDisclaimer: SCHEME_DATA_DISCLAIMER };
}

export async function mockGetScheme(id: string): Promise<Scheme> {
  await delay(200);
  const scheme = MOCK_SCHEMES.find((s) => s.id === id);
  if (!scheme) throw new Error(`Mock: no scheme with id "${id}"`);
  return scheme;
}

export async function mockRecommend(req: RecommendationRequest): Promise<RecommendationResponse> {
  await delay(700); // recommendation feels like "thinking"
  const result = recommendSchemes(MOCK_SCHEMES, req.profile, req.limit ?? 5);
  // The mock stands in for the server, so don't claim we were offline.
  return { ...result, offline: false };
}

export async function mockSearchPartners(
  req: PartnerSearchRequest,
): Promise<PartnerSearchResponse> {
  await delay();

  const origin = req.location;
  let items: ChannelPartner[] = MOCK_PARTNERS.map((p) => ({
    ...p,
    distanceKm: origin && p.location ? haversineKm(origin, p.location) : undefined,
  }));

  if (req.pincode && !origin) {
    items = items.filter((p) => p.pincode.slice(0, 3) === req.pincode!.slice(0, 3));
  }

  if (req.schemeCategory) {
    items = items.filter((p) => p.supportedSchemeCategories.includes(req.schemeCategory!));
  }

  if (req.schemeId) {
    items = items.filter(
      (p) => p.supportedSchemeIds.length === 0 || p.supportedSchemeIds.includes(req.schemeId!),
    );
  }

  if (req.partnerTypes?.length) {
    items = items.filter((p) => req.partnerTypes!.includes(p.type));
  }

  if (origin) {
    items = items.filter((p) => (p.distanceKm ?? Infinity) <= req.radiusKm);
  }

  items.sort((a, b) => (a.distanceKm ?? Infinity) - (b.distanceKm ?? Infinity));

  // The routing rule: don't send people to partners that can't disburse.
  const accepting = items.filter((p) => p.eligibility.status !== 'NOT_ACCEPTING');
  const useFallback = req.onlyAccepting && accepting.length === 0 && items.length > 0;

  return {
    items: req.onlyAccepting && !useFallback ? accepting : items,
    fallbackUsed: useFallback,
    searchedFrom: origin,
    radiusKm: req.radiusKm,
  };
}

export async function mockGetPartner(id: string): Promise<ChannelPartner> {
  await delay(200);
  const partner = MOCK_PARTNERS.find((p) => p.id === id);
  if (!partner) throw new Error(`Mock: no partner with id "${id}"`);
  return partner;
}

export async function mockAssistantQuery(
  req: AssistantQueryRequest,
): Promise<AssistantQueryResponse> {
  await delay(900); // the RAG round trip will not be instant either
  return answerFromKnowledgeBase(req);
}
