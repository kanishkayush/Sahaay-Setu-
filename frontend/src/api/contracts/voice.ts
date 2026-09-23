import { z } from 'zod';
import { LanguageCodeSchema } from './common';

/**
 * Server-side speech-to-text (`POST /v1/assistant/transcribe`) — the backend
 * half of the voice pipeline.
 *
 * ⚠️  BACKEND CONTRACT FILE — see docs/API_CONTRACT.md
 * ⚠️  NOT YET IMPLEMENTED ON EITHER SIDE. This file fixes the shape so both
 *     teams can build against it; `detectProvider()` in
 *     src/features/voice/speechToText.ts deliberately does NOT claim the
 *     'backend' provider until the endpoint exists. Claiming a capability we
 *     cannot deliver is the exact failure ADR-010 forbids.
 *
 * The pipeline:
 *
 *   VOICE UI → Speech-to-Text → "text query" → POST /v1/assistant/query
 *            → ChatResponse → Text-to-Speech
 *
 * On web the first stage runs in the browser (Web Speech API) and `POST /v1/assistant/transcribe`
 * is not called. On native it has to be a server round-trip, because
 * on-device STT needs a config plugin and a custom dev build.
 *
 * ── NAMING ────────────────────────────────────────────────────────────────
 * The backend teammate's diagram calls the chat stage `/v1/chat`. This repo's
 * contract has always called it `POST /v1/assistant/query`
 * (docs/API_CONTRACT.md). Same endpoint, two names — reconcile before wiring,
 * and change it here rather than aliasing in the client.
 */

export const TranscriptionRequestSchema = z.object({
  /** base64-encoded audio. Keep clips short; the server may reject long ones. */
  audioBase64: z.string().min(1),
  /** Container/codec of the clip, e.g. 'audio/webm', 'audio/m4a'. */
  mimeType: z.string().min(1),
  /**
   * Expected language. Optional — the point of a multilingual product is that
   * a user should be able to just speak, so the server should detect when this
   * is absent rather than failing.
   */
  language: LanguageCodeSchema.optional(),
  sessionId: z.string().optional(),
});
export type TranscriptionRequest = z.infer<typeof TranscriptionRequestSchema>;

export const TranscriptionResponseSchema = z.object({
  /** The transcript. May be empty when nothing intelligible was heard. */
  text: z.string(),
  detectedLanguage: LanguageCodeSchema.optional(),
  /**
   * 0–1 engine confidence. The client shows the transcript for confirmation
   * below a threshold rather than sending it straight on — a misheard question
   * about a loan is worse than one extra tap.
   */
  confidence: z.number().min(0).max(1).optional(),
  durationMs: z.number().nonnegative().optional(),
});
export type TranscriptionResponse = z.infer<typeof TranscriptionResponseSchema>;
