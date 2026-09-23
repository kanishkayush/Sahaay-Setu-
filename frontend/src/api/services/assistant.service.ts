import { apiRequest } from '@/api/client';
import { USE_MOCK_API } from '@/api/config';
import { ENDPOINTS } from '@/api/endpoints';
import {
  AssistantQueryResponseSchema,
  type AssistantQueryRequest,
  type AssistantQueryResponse,
} from '@/api/contracts';
import { mockAssistantQuery } from '@/api/mock/server';
import { answerFromKnowledgeBase } from '@/api/mock/fixtures/assistant';

import { getDeviceUserId } from '@/api/services/profile.service';

/**
 * Multilingual AI assistant.
 *
 * The backend owns the real RAG pipeline. Until it exists — and whenever it is
 * unreachable — we degrade to the offline knowledge base rather than failing.
 * Degraded answers come back with `grounded: false` so the UI can warn the user.
 */
export async function askAssistant(
  request: AssistantQueryRequest,
  signal?: AbortSignal,
): Promise<AssistantQueryResponse> {
  if (USE_MOCK_API) return mockAssistantQuery(request);

  const userId = await getDeviceUserId();

  return await apiRequest(ENDPOINTS.assistant.query, AssistantQueryResponseSchema, {
    method: 'POST',
    body: request,
    headers: { 'X-User-Id': userId },
    timeoutMs: 60_000, // LLM round trips can take 30-60s
    signal,
  });
}
