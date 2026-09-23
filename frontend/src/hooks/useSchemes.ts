import { useQuery } from '@tanstack/react-query';
import { getScheme, listSchemes } from '@/api/services';

export const schemeKeys = {
  all: ['schemes'] as const,
  detail: (id: string) => ['schemes', id] as const,
};

export function useSchemes() {
  return useQuery({
    queryKey: schemeKeys.all,
    queryFn: listSchemes,
    // The catalogue changes rarely; keep it warm so offline users still see it.
    staleTime: 1000 * 60 * 60,
  });
}

export function useScheme(id: string | undefined) {
  return useQuery({
    queryKey: schemeKeys.detail(id ?? ''),
    queryFn: () => getScheme(id!),
    enabled: Boolean(id),
    staleTime: 1000 * 60 * 60,
  });
}
