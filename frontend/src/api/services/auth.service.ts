import { apiRequest } from '@/api/client';
import { z } from 'zod';
import { ENDPOINTS } from '@/api/endpoints';
import { USE_MOCK_API } from '@/api/config';
import { mockLogin } from '@/api/mock/server';

export const AuthResponseSchema = z.object({
  token: z.string(),
  userId: z.string(),
  phoneNumber: z.string(),
});
export type AuthResponse = z.infer<typeof AuthResponseSchema>;

export async function login(mobile: string): Promise<AuthResponse> {
  if (USE_MOCK_API) {
    return mockLogin(mobile);
  }
  // Hackathon bypass: directly hit /v1/auth/login
  return apiRequest('/v1/auth/login', AuthResponseSchema, {
    method: 'POST',
    body: { mobile },
  });
}

