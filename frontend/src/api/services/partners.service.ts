import { apiRequest } from '@/api/client';
import { USE_MOCK_API } from '@/api/config';
import { ENDPOINTS } from '@/api/endpoints';
import {
  ChannelPartnerSchema,
  PartnerSearchResponseSchema,
  type ChannelPartner,
  type PartnerSearchRequest,
  type PartnerSearchResponse,
} from '@/api/contracts';
import { mockGetPartner, mockSearchPartners } from '@/api/mock/server';

export async function searchPartners(
  request: PartnerSearchRequest,
): Promise<PartnerSearchResponse> {
  if (USE_MOCK_API) return mockSearchPartners(request);
  return apiRequest(ENDPOINTS.partners.search, PartnerSearchResponseSchema, {
    method: 'POST',
    body: request,
  });
}

export async function getPartner(id: string): Promise<ChannelPartner> {
  if (USE_MOCK_API) return mockGetPartner(id);
  return apiRequest(ENDPOINTS.partners.byId(id), ChannelPartnerSchema);
}
