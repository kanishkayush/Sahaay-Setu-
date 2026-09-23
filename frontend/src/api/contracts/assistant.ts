import { z } from 'zod';
import { CitationSchema, LanguageCodeSchema } from './common';

/**
 * Multilingual AI assistant (RAG) — the surface owned by the backend partner.
 *
 * ⚠️  BACKEND CONTRACT FILE — see docs/API_CONTRACT.md
 *
 * v0 client behaviour: POST /v1/assistant/query and render the answer with its
 * citations. Streaming (SSE) is a v1 upgrade — `AssistantStreamChunkSchema` below
 * fixes the chunk shape so both sides can agree on it now, but the client does
 * not consume it yet.
 */

export const ChatRoleSchema = z.enum(['user', 'assistant', 'system']);

export const ChatMessageSchema = z.object({
  id: z.string(),
  role: ChatRoleSchema,
  content: z.string(),
  /** Language the message was written/spoken in (may differ per turn). */
  language: LanguageCodeSchema.optional(),
  citations: z.array(CitationSchema).default([]),
  createdAt: z.string(),
  /** Client-side only: message failed to send and can be retried. */
  error: z.boolean().optional(),
});
export type ChatMessage = z.infer<typeof ChatMessageSchema>;

export const AssistantQueryRequestSchema = z.object({
  /** The user's question, in ANY supported language. */
  query: z.string().min(1).max(2000),
  /** Language to answer in. Backend should detect if omitted. */
  responseLanguage: LanguageCodeSchema,
  /** Prior turns for context; keep it short, the server may truncate. */
  history: z
    .array(ChatMessageSchema.pick({ role: true, content: true }))
    .max(20)
    .default([]),
  /** Lets the RAG layer personalise answers. Optional — never required. */
  profileContext: z
    .object({
      annualFamilyIncome: z.number().optional(),
      projectType: z.string().optional(),
      stateCode: z.string().optional(),
    })
    .optional(),
  sessionId: z.string().optional(),
  guideMe: z.boolean().optional(),
});
export type AssistantQueryRequest = z.infer<typeof AssistantQueryRequestSchema>;

/**
 * The assistant may propose an in-app action. The client renders these as
 * tappable chips (e.g. "Open EMI calculator with ₹2,00,000 pre-filled").
 */
export const AssistantActionSchema = z.discriminatedUnion('type', [
  z.object({ type: z.literal('OPEN_SCHEME'), schemeId: z.string(), label: z.string() }),
  z.object({ type: z.literal('OPEN_PARTNER'), partnerId: z.string(), label: z.string() }),
  z.object({
    type: z.literal('OPEN_CALCULATOR'),
    label: z.string(),
    principal: z.number().optional(),
    annualRatePct: z.number().optional(),
    tenureMonths: z.number().optional(),
  }),
  z.object({ type: z.literal('START_RECOMMENDER'), label: z.string() }),
  z.object({ type: z.literal('OPEN_URL'), url: z.string().url(), label: z.string() }),
]);
export type AssistantAction = z.infer<typeof AssistantActionSchema>;

export const AssistantUICardSchema = z.discriminatedUnion('type', [
  z.object({
    type: z.literal('SCHEME_CARD'),
    schemeId: z.string(),
    schemeName: z.string(),
    reason: z.string().optional(),
    eligible: z.boolean().optional(),
  }),
  z.object({
    type: z.literal('ELIGIBILITY_CARD'),
    title: z.string(),
    details: z.string(),
  }),
  z.object({
    type: z.literal('NEXT_QUESTION_CARD'),
    question: z.string(),
    options: z.array(z.string()),
  }),
  z.object({
    type: z.literal('DOCUMENT_CHECKLIST'),
    requiredByScheme: z.array(z.string()),
    requiredByPartner: z.array(z.string()),
    recommended: z.array(z.string()),
  }),
  z.object({
    type: z.literal('PARTNER_CARD'),
    partnerId: z.string().nullable().optional(),
    name: z.string().optional(),
    distanceKm: z.number().optional(),
    address: z.string().optional(),
  }),
  z.object({
    type: z.literal('APPLICATION_STEP_CARD'),
    stepNumber: z.number(),
    title: z.string(),
    description: z.string(),
  }),
  z.object({
    type: z.literal('WARNING_CARD'),
    message: z.string(),
  }),
]);
export type AssistantUICard = z.infer<typeof AssistantUICardSchema>;

export const AssistantQueryResponseSchema = z.object({
  messageId: z.string(),
  answer: z.string(),
  answerLanguage: LanguageCodeSchema,
  /** Language the backend detected in the incoming query. */
  detectedQueryLanguage: LanguageCodeSchema.nullish(),
  citations: z.array(CitationSchema).default([]),
  suggestedActions: z.array(AssistantActionSchema).default([]),
  uiCards: z.array(AssistantUICardSchema).default([]),
  /** Follow-up questions rendered as chips under the answer. */
  followUpQuestions: z.array(z.string()).default([]),
  /** False → UI shows "I'm not sure, please verify with a Channel Partner". */
  grounded: z.boolean().default(true),
  sessionId: z.string().nullish(),
  /**
   * The Guided Journey field the backend is currently waiting for.
   * Frontend uses this to choose the correct input mode (PIN keypad, voice, etc.)
   * rather than inferring from translated question text.
   */
  expectedField: z
    .enum(['pinCode', 'existingBusiness', 'estimatedProjectCost', 'general'])
    .nullish(),
});
export type AssistantQueryResponse = z.infer<typeof AssistantQueryResponseSchema>;

/** v1: SSE streaming chunks. Contract only — not yet consumed by the client. */
export const AssistantStreamChunkSchema = z.discriminatedUnion('type', [
  z.object({ type: z.literal('token'), text: z.string() }),
  z.object({ type: z.literal('citations'), citations: z.array(CitationSchema) }),
  z.object({ type: z.literal('actions'), actions: z.array(AssistantActionSchema) }),
  z.object({ type: z.literal('cards'), cards: z.array(AssistantUICardSchema) }),
  z.object({ type: z.literal('done'), messageId: z.string() }),
  z.object({ type: z.literal('error'), message: z.string() }),
]);
export type AssistantStreamChunk = z.infer<typeof AssistantStreamChunkSchema>;
