import { apiRequest } from '@/api/client';
import { USE_MOCK_API } from '@/api/config';
import { ENDPOINTS } from '@/api/endpoints';
import {
  SchemeListResponseSchema,
  SchemeSchema,
  type Scheme,
  type SchemeListResponse,
} from '@/api/contracts';
import { mockGetScheme, mockListSchemes } from '@/api/mock/server';

/**
 * Scheme catalogue.
 * Every service follows this shape: mock branch first, then the real call.
 * Screens import ONLY from services (via hooks) — never from `mock/`.
 */

export async function listSchemes(): Promise<SchemeListResponse> {
  if (USE_MOCK_API) return mockListSchemes();
  return apiRequest(ENDPOINTS.schemes.list, SchemeListResponseSchema);
}

export async function getScheme(id: string): Promise<Scheme> {
  if (USE_MOCK_API) return mockGetScheme(id);
  return apiRequest(ENDPOINTS.schemes.byId(id), SchemeSchema);
}
