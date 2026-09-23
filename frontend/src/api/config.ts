import Constants from 'expo-constants';

/**
 * Runtime API configuration.
 *
 * The whole app talks to the backend through `src/api/*`. Flipping
 * `USE_MOCK_API` to false is the ONLY change needed to point the client at the
 * real backend — no screen or component imports `fetch` directly.
 *
 * ⚠️  Env vars MUST be read as literal `process.env.EXPO_PUBLIC_X` expressions.
 * Expo inlines them at build time by static text substitution, so a dynamic
 * lookup like `process.env[key]` compiles to `undefined` in a release build and
 * silently falls back to defaults. Add new vars to the block below, and to
 * `.env.example`.
 */

type Extra = {
  apiBaseUrl?: string;
  useMockApi?: string | boolean;
};

const extra = (Constants.expoConfig?.extra ?? {}) as Extra;

const ENV = {
  apiBaseUrl: process.env.EXPO_PUBLIC_API_BASE_URL,
  useMockApi: process.env.EXPO_PUBLIC_USE_MOCK_API,
  apiTimeoutMs: process.env.EXPO_PUBLIC_API_TIMEOUT_MS,
  mockLatencyMs: process.env.EXPO_PUBLIC_MOCK_LATENCY_MS,
} as const;

const nonEmpty = (value: string | undefined) => (value && value.length > 0 ? value : undefined);

export const API_BASE_URL = nonEmpty(ENV.apiBaseUrl) ?? extra.apiBaseUrl ?? 'http://localhost:8000';

/**
 * Defaults to TRUE so the app is fully demoable with zero backend running.
 * Set EXPO_PUBLIC_USE_MOCK_API=false in .env once the backend is up.
 */
export const USE_MOCK_API = false;

export const API_TIMEOUT_MS = Number(nonEmpty(ENV.apiTimeoutMs) ?? 15000);

/** Simulated latency for the mock server, so loading states are real. */
export const MOCK_LATENCY_MS = Number(nonEmpty(ENV.mockLatencyMs) ?? 450);

export const API_VERSION = 'v1';
