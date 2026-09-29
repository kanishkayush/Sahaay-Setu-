import { apiRequest } from '@/api/client';
import { z } from 'zod';
import { USE_MOCK_API } from '@/api/config';
import { mockLogin } from '@/api/mock/server';
import { normalizeIndianMobile } from '@/auth/indianMobile';

export const AuthResponseSchema = z.object({
  token: z.string(),
  userId: z.string(),
  phoneNumber: z.string(),
});
export type AuthResponse = z.infer<typeof AuthResponseSchema>;

export async function login(mobile: string): Promise<AuthResponse> {
  const phone = normalizeIndianMobile(mobile);
  if (!phone) {
    throw new Error('Invalid Indian mobile number. Enter a 10-digit number starting with 6, 7, 8 or 9.');
  }
  if (USE_MOCK_API) {
    return mockLogin(phone);
  }
  return apiRequest('/v1/auth/login', AuthResponseSchema, {
    method: 'POST',
    body: { mobile: phone },
  });
}

