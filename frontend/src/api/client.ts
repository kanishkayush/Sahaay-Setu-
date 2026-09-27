import type { z } from 'zod';
import { API_BASE_URL, API_TIMEOUT_MS } from './config';
import { ApiErrorSchema, type ApiError } from './contracts/common';
import { useAppStore } from '@/store/useAppStore';

/**
 * Thin typed fetch wrapper. Every response is validated against its Zod schema
 * before it reaches a screen, so a backend contract break fails loudly here
 * instead of silently rendering `undefined` three screens deep.
 */

export class ApiRequestError extends Error {
  readonly apiError: ApiError;
  readonly status: number;

  constructor(status: number, apiError: ApiError) {
    super(apiError.message);
    this.name = 'ApiRequestError';
    this.status = status;
    this.apiError = apiError;
  }
}

export class ContractViolationError extends Error {
  readonly issues: z.ZodIssue[];
  constructor(path: string, issues: z.ZodIssue[]) {
    super(
      `Response from ${path} did not match the agreed contract. ` +
        `Fix the backend or update src/api/contracts. Issues: ${JSON.stringify(issues.slice(0, 3))}`,
    );
    this.name = 'ContractViolationError';
    this.issues = issues;
  }
}

type RequestOptions = {
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE';
  body?: unknown;
  headers?: Record<string, string>;
  signal?: AbortSignal;
  timeoutMs?: number;
};

function toApiError(status: number, payload: unknown): ApiError {
  const parsed = ApiErrorSchema.safeParse(payload);
  if (parsed.success) return parsed.data;
  return {
    code:
      status === 404
        ? 'NOT_FOUND'
        : status === 401
          ? 'UNAUTHORIZED'
          : status === 429
            ? 'RATE_LIMITED'
            : status >= 500
              ? 'INTERNAL'
              : 'BAD_REQUEST',
    messageKey: 'errors.generic',
    message: `Request failed with status ${status}`,
  };
}

export async function apiRequest<TSchema extends z.ZodTypeAny>(
  path: string,
  schema: TSchema,
  options: RequestOptions = {},
): Promise<z.infer<TSchema>> {
  const { method = 'GET', body, headers = {}, signal, timeoutMs = API_TIMEOUT_MS } = options;

  // Create a dedicated controller for the fetch request
  const fetchController = new AbortController();
  
  // Set up timeout
  const timeout = setTimeout(() => fetchController.abort(), timeoutMs);

  // If caller provided a signal, wire it up to abort our fetchController
  if (signal) {
    if (signal.aborted) {
      fetchController.abort();
    } else {
      const onAbort = () => fetchController.abort();
      signal.addEventListener('abort', onAbort);
      // Clean up the listener when the request finishes (handled in finally block below,
      // but we need to track it)
      (fetchController as any)._callerSignal = signal;
      (fetchController as any)._onAbort = onAbort;
    }
  }

  const combinedSignal = fetchController.signal;

  try {
    const isFormData = body instanceof FormData;
    const requestHeaders: Record<string, string> = {
      Accept: 'application/json',
      ...headers,
    };
    
    // Inject Bearer token if available
    const token = useAppStore.getState().authToken;
    if (token && !requestHeaders['Authorization']) {
      requestHeaders['Authorization'] = `Bearer ${token}`;
    }

    if (!isFormData && !requestHeaders['Content-Type']) {
      requestHeaders['Content-Type'] = 'application/json';
    }

    const response = await fetch(`${API_BASE_URL}${path}`, {
      method,
      headers: requestHeaders,
      body: body === undefined ? undefined : isFormData ? (body as any) : JSON.stringify(body),
      signal: combinedSignal,
    });

    const text = await response.text();
    const payload: unknown = text.length > 0 ? JSON.parse(text) : null;

    if (!response.ok) {
      throw new ApiRequestError(response.status, toApiError(response.status, payload));
    }

    const parsed = schema.safeParse(payload);
    if (!parsed.success) {
      throw new ContractViolationError(path, parsed.error.issues);
    }
    return parsed.data;
  } finally {
    clearTimeout(timeout);
    if ((fetchController as any)._callerSignal && (fetchController as any)._onAbort) {
      (fetchController as any)._callerSignal.removeEventListener('abort', (fetchController as any)._onAbort);
    }
  }
}
