import { useEffect, useState } from 'react';
import type { LanguageCode } from '@/api/contracts';
import { canSpeak } from '@/features/voice/textToSpeech';

/**
 * Whether this device has a voice for `language`, so a screen can hide its
 * read-aloud control instead of producing gibberish.
 *
 * Starts optimistic. The check is a fast local lookup, and briefly showing a
 * control that then disappears is better than briefly hiding one that works —
 * the first is a flicker, the second reads as "the app has no voice feature".
 */
export function useCanSpeak(language: LanguageCode): boolean {
  const [supported, setSupported] = useState(true);

  useEffect(() => {
    let active = true;
    void canSpeak(language).then((ok) => {
      if (active) setSupported(ok);
    });
    return () => {
      active = false;
    };
  }, [language]);

  return supported;
}
