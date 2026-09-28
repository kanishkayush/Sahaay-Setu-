import { useCallback, useRef, useState } from 'react';
import type { AssistantAction, Citation, LanguageCode } from '@/api/contracts';
import { askAssistant } from '@/api/services';
import { canSpeak as canSpeakLanguage, speak, stopSpeaking } from '@/features/voice/textToSpeech';
import { useCanSpeak } from './useCanSpeak';
import { useSpeechInput, type SpeechInputError } from './useSpeechInput';
import { useQueryClient } from '@tanstack/react-query';
import { acceptAdviserSessionId, getAdviserSessionId } from '@/features/adviser/session';
import { buildAssistantProfileContext } from '@/features/adviser/profileContext';

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

export type VoiceError = SpeechInputError | 'CHAT_FAILED' | 'EMPTY_TRANSCRIPT' | 'TTS_ERROR';

export type VoiceTurn = {
  question: string;
  answer: string;
  citations: Citation[];
  actions: AssistantAction[];
  uiCards: import('@/api/contracts').AssistantUICard[];
  followUps: string[];
  answerLanguage: LanguageCode;
  /** False → the assistant could not ground the answer; the UI must warn. */
  grounded: boolean;
  sessionId?: string;
  /** Which Guided Journey field the backend is waiting for next. */
  expectedField?: 'pinCode' | 'existingBusiness' | 'estimatedProjectCost' | 'requestedLoanAmount' | 'activity' | 'annualFamilyIncome' | 'scEligibilityStatus' | 'general' | null;
};

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
  const requestInFlight = useRef(false);

  const ask = useCallback(
    async (question: string) => {
      const trimmed = question.trim();
      if (!trimmed) {
        // Never send an empty query to the backend.
        setChatError('EMPTY_TRANSCRIPT');
        setBusyPhase('idle');
        return;
      }
      // A recognition engine may emit the same final event twice. One active
      // utterance owns exactly one adviser request.
      if (requestInFlight.current) return;
      requestInFlight.current = true;

      // Ensure we have a stable session ID before the first request.
      if (!sessionId.current) {
        sessionId.current = getAdviserSessionId();
      }

      generation.current += 1;
      const mine = generation.current;
      // Keep the visible transcript faithful to the STT provider. Trimming is
      // only used for the backend query.
      setTranscript(question);
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
        const persistentProfile = queryClient.getQueryData<import('@/api/contracts').UserProfile>(['profile']);

        const response = await askAssistant({
          query: trimmed,
          responseLanguage: apiLanguage,
          history: [],
          profileContext: buildAssistantProfileContext(persistentProfile),
          sessionId: sessionId.current,
          guideMe: true,
        }, abortController.current.signal);
        
        console.log('[VOICE] API response language:', response.answerLanguage);
        console.log('[VOICE] Assistant text:', response.answer);

        // Discard stale responses from prior turns.
        if (generation.current !== mine) return;

        // Update sessionId if backend echoes one (it should match what we sent).
        if (response.sessionId) {
          sessionId.current = acceptAdviserSessionId(response.sessionId);
        }

        setTurn({
          question,
          answer: response.answer,
          citations: response.citations,
          actions: response.suggestedActions,
          uiCards: response.uiCards ?? [],
          followUps: response.followUpQuestions,
          answerLanguage: response.answerLanguage,
          grounded: response.grounded,
          sessionId: sessionId.current,
          expectedField: response.expectedField ?? null,
        });

        // Invalidate the persistent profile in the background so the Profile tab reflects
        // any new data (like PIN or name) the backend saved during this Guided Journey turn.
        void queryClient.invalidateQueries({ queryKey: ['profile'] });

        // No voice for this language: leave the answer on screen rather than
        // reading it in the wrong phonetics and reporting success.
        const responseCanRead = await canSpeakLanguage(response.answerLanguage);
        if (!responseCanRead) {
          requestInFlight.current = false;
          setBusyPhase('idle');
          return;
        }
        setBusyPhase('speaking');
        speak(response.answer, response.answerLanguage, {
          onDone: () => {
            if (generation.current === mine) {
              requestInFlight.current = false;
              setBusyPhase('idle');
            }
          },
          onError: () => {
            if (generation.current === mine) {
              setChatError('TTS_ERROR');
              requestInFlight.current = false;
              setBusyPhase('idle');
            }
          },
        });
      } catch (e) {
        // Only update UI for the current generation.
        if (generation.current !== mine) return;
        console.error('[VOICE] API Error:', e);
        setChatError('CHAT_FAILED');
        requestInFlight.current = false;
        setBusyPhase('idle');
      }
    },
    [language, queryClient],
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
    requestInFlight.current = false;
    setBusyPhase('idle');
  }, [speech]);

  /** Clear the currently displayed assistant response (turn/transcript) and stop speaking. */
  const clearLastResponse = useCallback(() => {
    generation.current += 1; // Discard any pending results for this generation
    stopSpeaking();
    requestInFlight.current = false;
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
    speak(turn.answer, turn.answerLanguage, {
      onDone: () => {
        if (generation.current === mine) setBusyPhase('idle');
      },
    });
  }, [canRead, turn]);

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
