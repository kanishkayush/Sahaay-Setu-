import * as Speech from 'expo-speech';
import type { LanguageCode } from '@/api/contracts';
import { speechLocaleFor } from './speechLocales';

/**
 * Text-to-speech — the last stage of the voice pipeline.
 *
 * Wraps expo-speech so the voice screen and the chat screen speak with the
 * same voice, rate and locale rather than each configuring it inline.
 *
 * Uses an async stop guard to prevent the race condition where
 * Speech.stop() + Speech.speak() in immediate succession causes silence
 * on Expo Web / browser TTS engines.
 */

const RATE = 0.9;

let voicesPromise: Promise<Speech.Voice[]> | null = null;

function loadVoices(): Promise<Speech.Voice[]> {
  voicesPromise ??= Speech.getAvailableVoicesAsync().catch(() => []);
  return voicesPromise;
}

export async function canSpeak(language: LanguageCode): Promise<boolean> {
  const voices = await loadVoices();
  if (voices.length === 0) return true;
  const base = speechLocaleFor(language).split('-')[0];
  return voices.some((v) => v.language.split(/[-_]/)[0] === base);
}

export type SpeakHandlers = {
  onStart?: () => void;
  onDone?: () => void;
  onError?: () => void;
};

/**
 * Prepare text for TTS output. For Hindi, replaces ASCII digits with
 * Hindi word equivalents so the TTS engine does not switch to English phonetics
 * mid-sentence (e.g. "6" -> "छह", "801503" -> "आठ शून्य एक पाँच शून्य तीन").
 * The UI text is NEVER modified — only the text sent to the speech engine.
 * Always defensive: if normalization fails, falls back to original text.
 */
export function prepareTextForSpeech(text: string, language: LanguageCode): string {
  if (!text || !text.trim()) return '';
  try {
    if (language !== 'hi') return text.trim();

    const map: Record<string, string> = {
      '0': 'शून्य', '1': 'एक', '2': 'दो', '3': 'तीन', '4': 'चार',
      '5': 'पाँच', '6': 'छह', '7': 'सात', '8': 'आठ', '9': 'नौ',
    };

    // Only replace isolated ASCII digits so multi-digit numbers (like PINs or Loan amounts)
    // are spoken natively by the TTS engine (e.g. 150000 -> "एक लाख पचास हजार").
    const normalized = text.replace(/(?<!\d)(\d)(?!\d)/g, (match) => {
      return map[match] ?? match;
    });

    return normalized.trim() || text.trim();
  } catch (error) {
    console.error('[TTS] Normalization failed, using original:', error);
    return text.trim();
  }
}

export function speak(text: string, language: LanguageCode, handlers: SpeakHandlers = {}) {
  if (!text.trim()) {
    handlers.onDone?.();
    return;
  }

  const speechLocale = speechLocaleFor(language);
  const normalizedText = prepareTextForSpeech(text, language);

  console.log('[TTS] API language:', language);
  console.log('[TTS] Speech locale:', speechLocale);
  console.log('[TTS] Original response:', text);
  console.log('[TTS] Speech-normalized text:', normalizedText);
  console.log('[TTS] Full text length:', normalizedText.length);

  const doSpeak = async () => {
    if (!normalizedText || normalizedText.trim().length === 0) {
      console.warn('[TTS] Empty speech text after normalization');
      handlers.onDone?.();
      return;
    }

    console.log('[TTS] Calling Speech.speak with complete text');
    handlers.onStart?.();

    let voiceIdentifier: string | undefined;
    // Select the best voice for the requested language (not just Hindi)
    const voices = await loadVoices();
    const targetLocale = speechLocaleFor(language);
    const baseCode = targetLocale.split('-')[0];
    const bestVoice =
      voices.find((v) => v.language === targetLocale) ??
      voices.find((v) => v.language.startsWith(baseCode));

    if (bestVoice) {
      voiceIdentifier = bestVoice.identifier;
      console.log(`[TTS] Selected ${language} voice:`, bestVoice.name, bestVoice.language);
    } else if (voices.length > 0) {
      console.warn(`[TTS] No voice found for ${language} (${targetLocale}). Available:`,
        voices.filter((v) => v.language.startsWith(baseCode)).map((v) => v.language));
    }

    Speech.speak(normalizedText, {
      language: speechLocale,
      voice: voiceIdentifier,
      rate: RATE,
      pitch: 1.0,
      onDone: handlers.onDone,
      onStopped: handlers.onDone,
      onError: handlers.onError ?? handlers.onDone,
    });
  };

  Speech.isSpeakingAsync()
    .then((isSpeaking) => {
      if (isSpeaking) {
        Speech.stop();
        setTimeout(doSpeak, 150);
      } else {
        doSpeak();
      }
    })
    .catch(() => {
      Speech.stop();
      doSpeak();
    });
}

export function stopSpeaking() {
  Speech.stop();
}
