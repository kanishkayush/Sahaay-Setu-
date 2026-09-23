import { z } from 'zod';

/**
 * Shared primitives for every request/response in the Sahaay Setu API.
 *
 * ⚠️  BACKEND CONTRACT FILE — do not change loosely.
 * These Zod schemas are the single source of truth shared between the
 * React Native client and the FastAPI/Node backend. If a field changes here,
 * it MUST change on the server in the same PR (see docs/API_CONTRACT.md).
 */

/** BCP-47-ish language codes the platform ships with. */
export const LanguageCodeSchema = z.enum([
  'en', // English
  'hi', // हिन्दी
  'mr', // मराठी
  'bn', // বাংলা
  'ta', // தமிழ்
  'te', // తెలుగు
]);
export type LanguageCode = z.infer<typeof LanguageCodeSchema>;

/** Amounts are always integer paise-free rupees to avoid float drift. */
export const RupeesSchema = z.number().int().nonnegative();

export const GeoPointSchema = z.object({
  latitude: z.number().min(-90).max(90),
  longitude: z.number().min(-180).max(180),
});
export type GeoPoint = z.infer<typeof GeoPointSchema>;

/** Machine-readable error envelope. `messageKey` maps to an i18n key. */
export const ApiErrorSchema = z.object({
  code: z.enum([
    'BAD_REQUEST',
    'UNAUTHORIZED',
    'NOT_FOUND',
    'RATE_LIMITED',
    'UPSTREAM_UNAVAILABLE',
    'INTERNAL',
  ]),
  messageKey: z.string(),
  message: z.string(),
  details: z.record(z.string(), z.unknown()).optional(),
  requestId: z.string().optional(),
});
export type ApiError = z.infer<typeof ApiErrorSchema>;

/**
 * Anything the RAG pipeline returns must carry its sources so the UI can show
 * "why did it say this". No citation → we render it as unverified.
 */
export const CitationSchema = z.object({
  id: z.string(),
  title: z.string(),
  /** e.g. "NSFDC Circular 2024-25/12, para 4.2" */
  locator: z.string().nullish(),
  url: z.string().url().nullish(),
  snippet: z.string().nullish(),
  confidence: z.number().min(0).max(1).nullish(),
});
export type Citation = z.infer<typeof CitationSchema>;

/**
 * `GET /v1/health` — the connectivity probe, and the first thing the backend
 * should stand up. It is deliberately trivial: if this parses, the base URL,
 * TLS, routing and the `/v1` prefix are all correct, which removes four
 * possible causes before anyone debugs a real endpoint.
 */
export const HealthResponseSchema = z.object({
  status: z.enum(['ok', 'degraded']),
  /** Free-form build or commit identifier, for matching client bugs to a deploy. */
  version: z.string().optional(),
  /** ISO-8601. Useful for spotting a clock skew between client and server. */
  time: z.string().optional(),
});
export type HealthResponse = z.infer<typeof HealthResponseSchema>;
