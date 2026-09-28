import { useCallback, useRef, useState } from 'react';
import { askAssistant } from '@/api/services';
import type { ChatMessage, LanguageCode, UserProfile } from '@/api/contracts';
import { useQueryClient } from '@tanstack/react-query';
import {
  acceptAdviserSessionId,
  getAdviserSessionId,
  resetAdviserSession,
} from '@/features/adviser/session';
import { buildAssistantProfileContext } from '@/features/adviser/profileContext';

let idCounter = 0;
const nextId = () => `local-${Date.now()}-${(idCounter += 1)}`;

/**
 * Chat state for the multilingual assistant.
 *
 * Kept as a hook rather than in the global store because a conversation is
 * session-scoped — we deliberately do not persist question history to disk.
 */
export function useAssistant(language: LanguageCode) {
  const queryClient = useQueryClient();
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
        const persistentProfile = queryClient.getQueryData<UserProfile>(['profile']);
        const response = await askAssistant({
          query: trimmed,
          responseLanguage: language,
          history,
          profileContext: buildAssistantProfileContext(persistentProfile),
          sessionId: sessionId.current ?? getAdviserSessionId(),
          guideMe: true,
        });
        sessionId.current = acceptAdviserSessionId(response.sessionId ?? undefined);

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
    [isThinking, language, messages, queryClient],
  );

  const clear = useCallback(() => {
    setMessages([]);
    sessionId.current = undefined;
    resetAdviserSession();
  }, []);

  return { messages, isThinking, send, clear };
}
