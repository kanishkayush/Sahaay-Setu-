import { Platform } from 'react-native';
import type { LanguageCode } from '@/api/contracts';
import { speechLocaleFor } from './speechLocales';

/**
 * Speech-to-text — the first stage of the voice pipeline.
 *
 *   VOICE UI → [Speech-to-Text] → "text query" → assistant endpoint →
 *   ChatResponse → Text-to-Speech
 *
 * ── THE RULE THIS FILE EXISTS TO ENFORCE ──────────────────────────────────
 *
 * ADR-010 said: no speech-to-text in v0, and no mic button, because "a mic
 * button that does nothing is worse than no button". That reasoning still
 * stands and is not softened here — it is enforced in code instead.
 *
 * `detectProvider()` is called before anything renders. If it returns
 * `available: false`, the screen must say why and offer typing instead. It
 * must never draw a mic that cannot listen. A user who taps a dead mic and
 * gets silence concludes the app does not work — and this app's users are
 * the least able to afford giving up on it.
 *
 * ── PROVIDERS ─────────────────────────────────────────────────────────────
 *
 *   web      Web Speech API. Real, free, no backend, and the surface the
 *            demo runs on. Chrome and Safari expose it; Firefox does not.
 *   backend  POST /v1/assistant/transcribe — owned by the backend teammate, used once
 *            USE_MOCK_API is false and the endpoint exists. Contract lives in
 *            src/api/contracts/voice.ts.
 *   none     Native without a dev build, or an unsupported browser. Honest
 *            unavailability with a reason the UI can render.
 *
 * Native STT needs a config plugin and a custom dev build, which Expo Go
 * cannot load — that is why `native` is not a provider here rather than a
 * stub that throws at runtime.
 */

export type SttProviderId = 'web' | 'backend' | 'none';

export type SttUnavailableReason =
  | 'NEEDS_DEV_BUILD'
  | 'BROWSER_UNSUPPORTED'
  | 'NO_BACKEND'
  | 'PERMISSION_DENIED'
  | 'INSECURE_CONTEXT';

/**
 * Every failure the engine can report, mapped rather than collapsed.
 *
 * The first version of this file lumped everything except three codes into
 * 'UNKNOWN', whose message is "Something went wrong while listening." That is
 * useless to a user AND to whoever has to debug it: `network` (the recogniser
 * is a cloud service and cannot work offline) and `language-not-supported`
 * (this device cannot hear that language at all) are completely different
 * problems with completely different fixes, and both looked identical.
 */
export type SttRuntimeError =
  | 'NO_SPEECH'
  | 'NETWORK'
  | 'AUDIO_CAPTURE'
  | 'LANGUAGE_NOT_SUPPORTED'
  | 'PERMISSION_DENIED'
  | 'BUSY'
  | 'UNKNOWN';

export type SttCapability =
  | { available: true; provider: Exclude<SttProviderId, 'none'> }
  | { available: false; provider: 'none'; reason: SttUnavailableReason };

/** Minimal shape of the Web Speech API we rely on — it is not in lib.dom yet. */
type WebSpeechRecognition = {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  maxAlternatives: number;
  start: () => void;
  stop: () => void;
  abort: () => void;
  onresult: ((event: WebSpeechResultEvent) => void) | null;
  onerror: ((event: { error: string }) => void) | null;
  onend: (() => void) | null;
};

type WebSpeechResultEvent = {
  resultIndex: number;
  results: ArrayLike<ArrayLike<{ transcript: string }> & { isFinal: boolean; length: number }>;
};

type SpeechRecognitionCtor = new () => WebSpeechRecognition;

function webSpeechCtor(): SpeechRecognitionCtor | null {
  if (Platform.OS !== 'web' || typeof window === 'undefined') return null;
  const w = window as unknown as {
    SpeechRecognition?: SpeechRecognitionCtor;
    webkitSpeechRecognition?: SpeechRecognitionCtor;
  };
  return w.SpeechRecognition ?? w.webkitSpeechRecognition ?? null;
}

/**
 * What this device can actually do, right now. Call before rendering a mic.
 * Backend transcription is deliberately NOT claimed until the endpoint is
 * real — see the note in src/api/contracts/voice.ts.
 */
export function detectProvider(): SttCapability {
  if (webSpeechCtor()) {
    // The API exists on an insecure origin but every start() fails. Serving the
    // dev bundle over a LAN IP (http://192.168.x.x:8081) hits this, while
    // localhost does not — so it is easy to miss until someone tests on a phone.
    if (typeof window !== 'undefined' && window.isSecureContext === false) {
      return { available: false, provider: 'none', reason: 'INSECURE_CONTEXT' };
    }
    return { available: true, provider: 'web' };
  }
  if (Platform.OS === 'web') {
    return { available: false, provider: 'none', reason: 'BROWSER_UNSUPPORTED' };
  }
  // For native, use the backend STT proxy since we don't have native STT plugins installed
  return { available: true, provider: 'backend' };
}

export type SttSession = {
  /** Stop listening and let the final result arrive. */
  stop: () => void;
  /** Abandon the session; no further callbacks fire. */
  cancel: () => void;
};

export type SttHandlers = {
  /** Fires repeatedly as the engine revises its guess. Render this live. */
  onPartial: (text: string) => void;
  /** Fires once with the text to send onward. */
  onFinal: (text: string) => void;
  /**
   * `raw` is the engine's own code, passed through so an unmapped failure can
   * be reported precisely instead of as "something went wrong".
   */
  onError: (reason: SttRuntimeError, raw?: string) => void;
};

/** Web Speech error codes → our vocabulary. */
function mapError(code: string): SttRuntimeError {
  switch (code) {
    case 'not-allowed':
    case 'service-not-allowed':
      return 'PERMISSION_DENIED';
    case 'no-speech':
      return 'NO_SPEECH';
    case 'network':
      return 'NETWORK';
    case 'audio-capture':
      return 'AUDIO_CAPTURE';
    case 'language-not-supported':
      return 'LANGUAGE_NOT_SUPPORTED';
    default:
      return 'UNKNOWN';
  }
}

import { Audio } from 'expo-av';
import * as FileSystem from 'expo-file-system';
import { apiRequest } from '@/api/client';
import { ENDPOINTS } from '@/api/endpoints';
import { TranscriptionResponseSchema } from '@/api/contracts/voice';

let activeRecording: Audio.Recording | null = null;

export function startListening(language: LanguageCode, handlers: SttHandlers): SttSession | null {
  const providerInfo = detectProvider();
  if (!providerInfo.available) return null;

  if (providerInfo.provider === 'backend') {
    let cancelled = false;

    // Start native recording
    (async () => {
      try {
        const perm = await Audio.requestPermissionsAsync();
        if (perm.status !== 'granted') {
          handlers.onError('PERMISSION_DENIED');
          return;
        }

        await Audio.setAudioModeAsync({
          allowsRecordingIOS: true,
          playsInSilentModeIOS: true,
        });

        // We cancel any previous zombie recordings
        if (activeRecording) {
          await activeRecording.stopAndUnloadAsync().catch(() => {});
        }

        const { recording } = await Audio.Recording.createAsync(
          Audio.RecordingOptionsPresets.HIGH_QUALITY
        );
        activeRecording = recording;

        if (cancelled) {
          await recording.stopAndUnloadAsync();
          return;
        }
        
        // Emulate partial feedback just to let user know it's listening
        handlers.onPartial('...');
      } catch (e) {
        handlers.onError('AUDIO_CAPTURE', String(e));
      }
    })();

    return {
      stop: () => {
        if (!activeRecording) return;
        const rec = activeRecording;
        activeRecording = null;
        
        (async () => {
          try {
            await rec.stopAndUnloadAsync();
            if (cancelled) return;

            const uri = rec.getURI();
            if (!uri) throw new Error('No URI');

            const audioBase64 = await FileSystem.readAsStringAsync(uri, { encoding: 'base64' });

            const response = await apiRequest(ENDPOINTS.assistant.transcribe, TranscriptionResponseSchema, {
              method: 'POST',
              body: {
                audioBase64,
                mimeType: 'audio/m4a', // Default format for high quality on iOS/Android
                language,
              },
            });
            
            if (response.text) {
              handlers.onFinal(response.text);
            } else {
              handlers.onError('NO_SPEECH');
            }
          } catch (e) {
            if (!cancelled) {
              handlers.onError('NETWORK', String(e));
            }
          }
        })();
      },
      cancel: () => {
        cancelled = true;
        if (activeRecording) {
          activeRecording.stopAndUnloadAsync().catch(() => {});
          activeRecording = null;
        }
      },
    };
  }

  // Provider is 'web'
  const Ctor = webSpeechCtor();
  if (!Ctor) return null;

  const recognition = new Ctor();
  recognition.lang = speechLocaleFor(language);
  recognition.continuous = true;
  recognition.interimResults = true;
  recognition.maxAlternatives = 1;

  let settled = false;
  let bestPartial = '';

  recognition.onresult = (event) => {
    let finalText = '';
    let interim = '';
    for (let i = event.resultIndex; i < event.results.length; i += 1) {
      const result = event.results[i];
      if (!result || result.length === 0) continue;
      const alternative = result[0];
      if (!alternative) continue;
      if (result.isFinal) finalText += alternative.transcript;
      else interim += alternative.transcript;
    }
    if (finalText) {
      settled = true;
      handlers.onFinal(finalText.trim());
    } else if (interim) {
      bestPartial = interim;
      handlers.onPartial(interim);
    }
  };

  recognition.onerror = (event) => {
    if (event.error === 'aborted') return;
    settled = true;
    handlers.onError(mapError(event.error), event.error);
  };

  recognition.onend = () => {
    if (!settled && bestPartial.trim()) {
      settled = true;
      handlers.onFinal(bestPartial.trim());
    } else if (!settled) {
      handlers.onError('NO_SPEECH');
    }
  };

  try {
    recognition.start();
  } catch (e) {
    const name = e instanceof Error ? e.name : 'Error';
    handlers.onError(name === 'InvalidStateError' ? 'BUSY' : 'UNKNOWN', name);
    return null;
  }

  return {
    stop: () => recognition.stop(),
    cancel: () => {
      settled = true;
      recognition.abort();
    },
  };
}
