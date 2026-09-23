import { useMutation } from '@tanstack/react-query';
import { getRecommendations } from '@/api/services';
import type { RecommendationRequest } from '@/api/contracts';

/**
 * A mutation rather than a query: the user explicitly asks for a match, and we
 * want a fresh answer each time they change their answers.
 */
export function useRecommendations() {
  return useMutation({
    mutationKey: ['recommendations'],
    mutationFn: (request: RecommendationRequest) => getRecommendations(request),
  });
}
