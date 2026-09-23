import { apiRequest } from '@/api/client';
import { USE_MOCK_API } from '@/api/config';
import { ENDPOINTS } from '@/api/endpoints';
import {
  RecommendationResponseSchema,
  type RecommendationRequest,
  type RecommendationResponse,
} from '@/api/contracts';
import { mockRecommend } from '@/api/mock/server';
import { MOCK_SCHEMES } from '@/api/mock/fixtures/schemes';
import { recommendSchemes } from '@/features/recommender/ruleEngine';

/**
 * Smart Scheme Recommender.
 *
 * Resilience is deliberate: if the AI backend is down or slow, we still answer
 * from the on-device rule engine rather than showing an error. A recommendation
 * computed offline is flagged `offline: true` and the UI says so.
 */
export async function getRecommendations(
  request: RecommendationRequest,
): Promise<RecommendationResponse> {
  if (USE_MOCK_API) return mockRecommend(request);

  try {
    return await apiRequest(ENDPOINTS.recommendations.create, RecommendationResponseSchema, {
      method: 'POST',
      body: request,
    });
  } catch (error) {
    if (__DEV__) {
      console.warn('[recommendations] backend unavailable, using on-device rules:', error);
    }
    return recommendSchemes(MOCK_SCHEMES, request.profile, request.limit ?? 5);
  }
}
