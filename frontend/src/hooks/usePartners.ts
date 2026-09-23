import { useQuery } from '@tanstack/react-query';
import { getPartner, searchPartners } from '@/api/services';
import type { PartnerSearchRequest } from '@/api/contracts';

export const partnerKeys = {
  search: (req: PartnerSearchRequest) => ['partners', 'search', req] as const,
  detail: (id: string) => ['partners', id] as const,
};

export function usePartnerSearch(request: PartnerSearchRequest, enabled = true) {
  return useQuery({
    queryKey: partnerKeys.search(request),
    queryFn: () => searchPartners(request),
    enabled,
    staleTime: 1000 * 60 * 5, // fund-health data goes stale quickly
  });
}

export function usePartner(id: string | undefined) {
  return useQuery({
    queryKey: partnerKeys.detail(id ?? ''),
    queryFn: () => getPartner(id!),
    enabled: Boolean(id),
  });
}
