import { useCallback, useEffect, useRef, useState } from 'react';
import type { AssistantAction, Citation, LanguageCode } from '@/api/contracts';
import { askAssistant } from '@/api/services';
import { speak, stopSpeaking } from '@/features/voice/textToSpeech';
import { useCanSpeak } from './useCanSpeak';
import { useSpeechInput, type SpeechInputError } from './useSpeechInput';
import { useQueryClient } from '@tanstack/react-query';

/**
 * The voice pipeline, as one state machine.
 *
 *   idle → listening → thinking → speaking → idle
 *            (STT)      (chat)      (TTS)
 *
 * Kept in a hook so the screen stays a rendering of `phase` and nothing else.
 * The screen must not call the STT or TTS modules directly — same rule as
 * screens never calling fetch. Listening itself lives in useSpeechInput, shared
 * with the chat screen.
 *
 * Session persistence:
 *   A stable UUID is generated on the first `ask()` call and reused for every
 *   subsequent turn in the same screen session. This lets the backend's state
 *   machine (guided_journey.py) advance deterministically without the user
 *   repeating themselves.
 *
 * Abort safety:
 *   The `generation` counter guards against stale async results. Only the most
 *   recent call to `ask()` is allowed to update the UI. The AbortController
 *   in apiRequest is NOT wired to component unmount — that caused premature
 *   cancellations in React strict mode.
 */

export type VoicePhase = 'idle' | 'listening' | 'thinking' | 'speaking';

export type VoiceError = SpeechInputError | 'CHAT_FAILED' | 'EMPTY_TRANSCRIPT';

export type VoiceTurn = {
  question: string;
  answer: string;
  citations: Citation[];
  actions: AssistantAction[];
  uiCards: import('@/api/contracts').AssistantUICard[];
  followUps: string[];
  /** False → the assistant could not ground the answer; the UI must warn. */
  grounded: boolean;
  sessionId?: string;
  /** Which Guided Journey field the backend is waiting for next. */
  expectedField?: 'pinCode' | 'existingBusiness' | 'estimatedProjectCost' | 'general' | null;
};

// Generate a UUID (RFC 4122 v4) without any external dependency.
function generateUUID(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }
  // Fallback for environments that lack crypto.randomUUID
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === 'x' ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

export function useVoiceQuery(language: LanguageCode) {
  const queryClient = useQueryClient();
  const canRead = useCanSpeak(language);
  const [busyPhase, setBusyPhase] = useState<'idle' | 'thinking' | 'speaking'>('idle');
  const [transcript, setTranscript] = useState('');
  const [turn, setTurn] = useState<VoiceTurn | null>(null);
  const [chatError, setChatError] = useState<VoiceError | null>(null);

  /**
   * Stable session ID for the lifetime of this hook instance.
   * Generated lazily on the first ask() call. Preserved across turns so the
   * backend can maintain conversation state (guided journey state machine).
   */
  const sessionId = useRef<string | undefined>(undefined);

  /**
   * Guards the ask/speak stages against a turn the user has since abandoned.
   * Incrementing this ref effectively "cancels" any pending async work from
   * prior turns without aborting the HTTP request (which avoids the strict-mode
   * double-mount cancellation bug).
   */
  const generation = useRef(0);
  const abortController = useRef<AbortController | null>(null);

  const ask = useCallback(
    async (question: string) => {
      const trimmed = question.trim();
      if (!trimmed) {
        // Never send an empty query to the backend.
        setChatError('EMPTY_TRANSCRIPT');
        setBusyPhase('idle');
        return;
      }

      // Ensure we have a stable session ID before the first request.
      if (!sessionId.current) {
        sessionId.current = generateUUID();
      }

      const mine = generation.current;
      setTranscript(trimmed);
      setBusyPhase('thinking');
      setChatError(null);

      abortController.current?.abort();
      abortController.current = new AbortController();

      // Pass the actual selected language — never silently convert to English.
      const apiLanguage = language;
      
      console.log('[VOICE] Selected app language:', language);
      console.log('[VOICE] API request language:', apiLanguage);
      console.log('[VOICE] Session ID:', sessionId.current);

      try {
        const response = await askAssistant({
          query: trimmed,
          responseLanguage: apiLanguage,
          history: [],
          sessionId: sessionId.current,
          guideMe: true,
        }, abortController.current.signal);
        
        console.log('[VOICE] API response language:', response.answerLanguage);
        console.log('[VOICE] Assistant text:', response.answer);

        // Discard stale responses from prior turns.
        if (generation.current !== mine) return;

        // Update sessionId if backend echoes one (it should match what we sent).
        if (response.sessionId) {
          sessionId.current = response.sessionId;
        }

        setTurn({
          question: trimmed,
          answer: response.answer,
          citations: response.citations,
          actions: response.suggestedActions,
          uiCards: response.uiCards ?? [],
          followUps: response.followUpQuestions,
          grounded: response.grounded,
          sessionId: sessionId.current,
          expectedField: response.expectedField ?? null,
        });

        // Invalidate the persistent profile in the background so the Profile tab reflects
        // any new data (like PIN or name) the backend saved during this Guided Journey turn.
        void queryClient.invalidateQueries({ queryKey: ['profile'] });

        // No voice for this language: leave the answer on screen rather than
        // reading it in the wrong phonetics and reporting success.
        if (!canRead) {
          setBusyPhase('idle');
          return;
        }
        setBusyPhase('speaking');
        speak(response.answer, language, {
          onDone: () => {
            if (generation.current === mine) setBusyPhase('idle');
          },
        });
      } catch (e) {
        // Only update UI for the current generation.
        if (generation.current !== mine) return;
        if (__DEV__) console.error('[VOICE] API Error:', e);
        setChatError('CHAT_FAILED');
        setBusyPhase('idle');
      }
    },
    [canRead, language],
  );

  const speech = useSpeechInput(language, {
    onPartial: setTranscript,
    onFinal: (text) => void ask(text),
  });

  // Removed stopSpeaking cleanup on unmount as it causes issues in React strict mode re-renders

  const phase: VoicePhase = speech.isListening ? 'listening' : busyPhase;

  const listen = useCallback(() => {
    if (phase !== 'idle') return;
    generation.current += 1;
    setTranscript('');
    setTurn(null);
    setChatError(null);
    speech.clearError();
    speech.start();
  }, [phase, speech]);

  /** Abandon the current turn entirely, whatever stage it is at. */
  const cancel = useCallback(() => {
    generation.current += 1;
    abortController.current?.abort();
    abortController.current = null;
    speech.cancel();
    stopSpeaking();
    setBusyPhase('idle');
  }, [speech]);

  /** Clear the currently displayed assistant response (turn/transcript) and stop speaking. */
  const clearLastResponse = useCallback(() => {
    generation.current += 1; // Discard any pending results for this generation
    stopSpeaking();
    setTranscript('');
    setTurn(null);
    setChatError(null);
    setBusyPhase('idle');
  }, []);

  /** Re-read the current answer without asking again. */
  const replay = useCallback(() => {
    if (!turn || !canRead) return;
    const mine = generation.current;
    setBusyPhase('speaking');
    speak(turn.answer, language, {
      onDone: () => {
        if (generation.current === mine) setBusyPhase('idle');
      },
    });
  }, [canRead, language, turn]);

  /** Expose the current sessionId for display in the debug panel. */
  const currentSessionId = sessionId.current;

  return {
    capability: speech.capability,
    /** False → this device has no voice for the language; don't offer read-aloud. */
    canSpeak: canRead,
    phase,
    transcript,
    turn,
    error: (chatError ?? speech.error) as VoiceError | null,
    /** Engine's own code when the mapped reason is UNKNOWN. */
    errorCode: speech.errorCode,
    listen,
    stopListening: speech.stop,
    cancel,
    clearLastResponse,
    replay,
    /** Text entry fallback — same pipeline from the "text query" stage on. */
    askText: ask,
    /** The stable session ID (undefined until first ask). */
    sessionId: currentSessionId,
  };
}
