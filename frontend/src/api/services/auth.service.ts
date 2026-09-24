import { apiRequest } from '@/api/client';
import { z } from 'zod';
import { ENDPOINTS } from '@/api/endpoints';
import { USE_MOCK_API } from '@/api/config';
import { mockSendOtp, mockVerifyOtp } from '@/api/mock/server';

export const SendOtpRequestSchema = z.object({
  phoneNumber: z.string(),
});
export type SendOtpRequest = z.infer<typeof SendOtpRequestSchema>;

export const SendOtpResponseSchema = z.object({
  status: z.string(),
  message: z.string(),
});
export type SendOtpResponse = z.infer<typeof SendOtpResponseSchema>;

export const VerifyOtpRequestSchema = z.object({
  phoneNumber: z.string(),
  otp: z.string(),
});
export type VerifyOtpRequest = z.infer<typeof VerifyOtpRequestSchema>;

export const AuthResponseSchema = z.object({
  token: z.string(),
  userId: z.string(),
  phoneNumber: z.string(),
});
export type AuthResponse = z.infer<typeof AuthResponseSchema>;

export async function sendOtp(phoneNumber: string): Promise<SendOtpResponse> {
  if (USE_MOCK_API) {
    return mockSendOtp(phoneNumber);
  }
  return apiRequest('/v1/auth/send-otp', SendOtpResponseSchema, {
    method: 'POST',
    body: { phoneNumber },
  });
}

export async function verifyOtp(phoneNumber: string, otp: string): Promise<AuthResponse> {
  if (USE_MOCK_API) {
    return mockVerifyOtp(phoneNumber, otp);
  }
  return apiRequest('/v1/auth/verify-otp', AuthResponseSchema, {
    method: 'POST',
    body: { phoneNumber, otp },
  });
}
