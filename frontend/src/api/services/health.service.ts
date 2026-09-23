import { apiRequest } from '@/api/client';
import { USE_MOCK_API } from '@/api/config';
import { ENDPOINTS } from '@/api/endpoints';
import { HealthResponseSchema, type HealthResponse } from '@/api/contracts';

/**
 * Connectivity probe. Step 1 of docs/BACKEND_HANDOFF.md § Suggested order —
 * it existed in the route table and in the handoff instructions but had no way
 * to call it, so "prove connectivity" was advice with nothing behind it.
 *
 * In mock mode it answers immediately rather than hitting the network, so the
 * same call is safe to make from either configuration.
 */
export async function checkHealth(): Promise<HealthResponse> {
  if (USE_MOCK_API) return { status: 'ok', version: 'mock', time: new Date().toISOString() };
  return apiRequest(ENDPOINTS.health, HealthResponseSchema);
}
