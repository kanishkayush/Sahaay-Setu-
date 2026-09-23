import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { LanguageCode } from '@/api/contracts';
import {
  detectProvider,
  startListening,
  type SttRuntimeError,
  type SttSession,
} from '@/features/voice/speechToText';

/**
 * One speech-to-text session, as React state.
 *
 * Shared by both voice surfaces so there is a single place where listening is
 * started, stopped, and torn down:
 *
 *   app/voice.tsx      → useVoiceQuery → here.  Transcript is SENT immediately.
 *   app/assistant.tsx  → here directly.         Transcript fills the composer.
 *
 * That difference is deliberate, not an inconsistency. The voice screen is a
 * single-shot question with an immediate spoken answer, so waiting for a second
 * tap would defeat it. The chat screen is a considered, multi-turn conversation
 * with an edit field already on screen — there, a misheard question about a loan
 * is worth one extra tap to correct before sending.
 */

export type SpeechInputError = SttRuntimeError;

export type UseSpeechInputOptions = {
  /** Called once per session with the final transcript. */
  onFinal: (text: string) => void;
  /** Called as the engine revises its guess. Omit to ignore interim results. */
  onPartial?: (text: string) => void;
};

export function useSpeechInput(
  language: LanguageCode,
  { onFinal, onPartial }: UseSpeechInputOptions,
) {
  const capability = useMemo(() => detectProvider(), []);

  const [isListening, setIsListening] = useState(false);
  const [error, setError] = useState<SpeechInputError | null>(null);
  /** The engine's own code. Shown alongside UNKNOWN so it can be reported. */
  const [errorCode, setErrorCode] = useState<string | null>(null);

  const session = useRef<SttSession | null>(null);
  // Discards callbacks from a session the user has already abandoned.
  const generation = useRef(0);

  // Callbacks are read through refs so a caller passing an inline arrow does not
  // tear down and restart the mic on every render.
  const handlers = useRef({ onFinal, onPartial });
  handlers.current = { onFinal, onPartial };

  useEffect(
    () => () => {
      session.current?.cancel();
    },
    [],
  );

  const start = useCallback(() => {
    if (!capability.available || isListening) return;
    generation.current += 1;
    const mine = generation.current;

    setError(null);
    setErrorCode(null);
    setIsListening(true);

    const safetyTimer = setTimeout(() => {
      if (generation.current === mine) {
        session.current?.stop();
      }
    }, 60000);

    session.current = startListening(language, {
      onPartial: (text) => {
        if (generation.current === mine) handlers.current.onPartial?.(text);
      },
      onFinal: (text) => {
        if (generation.current !== mine) return;
        clearTimeout(safetyTimer);
        setIsListening(false);
        handlers.current.onFinal(text);
      },
      onError: (reason, raw) => {
        if (generation.current !== mine) return;
        clearTimeout(safetyTimer);
        setIsListening(false);
        setError(reason);
        setErrorCode(raw ?? null);
      },
    });

    // startListening already reported through onError; don't overwrite its
    // more specific reason with a generic one.
    if (!session.current) setIsListening(false);
  }, [capability.available, isListening, language]);

  /** Stop the mic and let the final transcript arrive. */
  const stop = useCallback(() => {
    session.current?.stop();
  }, []);

  /** Abandon the session; no transcript, no callbacks. */
  const cancel = useCallback(() => {
    generation.current += 1;
    session.current?.cancel();
    session.current = null;
    setIsListening(false);
  }, []);

  /** Tap-to-toggle, which is how both screens drive the mic. */
  const toggle = useCallback(() => {
    if (isListening) stop();
    else start();
  }, [isListening, start, stop]);

  const clearError = useCallback(() => {
    setError(null);
    setErrorCode(null);
  }, []);

  return { capability, isListening, error, errorCode, start, stop, cancel, toggle, clearError };
}
