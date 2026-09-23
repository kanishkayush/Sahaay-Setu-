import { useCallback, useRef, useState } from 'react';
import { askAssistant } from '@/api/services';
import type { ChatMessage, LanguageCode } from '@/api/contracts';

let idCounter = 0;
const nextId = () => `local-${Date.now()}-${(idCounter += 1)}`;

/**
 * Chat state for the multilingual assistant.
 *
 * Kept as a hook rather than in the global store because a conversation is
 * session-scoped — we deliberately do not persist question history to disk.
 */
export function useAssistant(language: LanguageCode) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isThinking, setIsThinking] = useState(false);
  const sessionId = useRef<string | undefined>(undefined);

  const send = useCallback(
    async (text: string) => {
      const trimmed = text.trim();
      if (!trimmed || isThinking) return;

      const userMessage: ChatMessage = {
        id: nextId(),
        role: 'user',
        content: trimmed,
        language,
        citations: [],
        createdAt: new Date().toISOString(),
      };

      // Snapshot history BEFORE appending, so we don't send the new turn twice.
      const history = messages.slice(-10).map((m) => ({ role: m.role, content: m.content }));
      setMessages((prev) => [...prev, userMessage]);
      setIsThinking(true);

      try {
        const response = await askAssistant({
          query: trimmed,
          responseLanguage: language,
          history,
          sessionId: sessionId.current,
          guideMe: true,
        });
        sessionId.current = response.sessionId ?? sessionId.current;

        setMessages((prev) => [
          ...prev,
          {
            id: response.messageId,
            role: 'assistant',
            content: response.answer,
            language: response.answerLanguage,
            citations: response.citations,
            createdAt: new Date().toISOString(),
          },
        ]);
        return response;
      } catch {
        setMessages((prev) => [
          ...prev,
          {
            id: nextId(),
            role: 'assistant',
            content: '',
            citations: [],
            createdAt: new Date().toISOString(),
            error: true,
          },
        ]);
        return null;
      } finally {
        setIsThinking(false);
      }
    },
    [isThinking, language, messages],
  );

  const clear = useCallback(() => {
    setMessages([]);
    sessionId.current = undefined;
  }, []);

  return { messages, isThinking, send, clear };
}
