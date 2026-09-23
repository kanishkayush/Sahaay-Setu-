import { useRef, useState } from 'react';
import {
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  TextInput,
  View,
} from 'react-native';
import { router } from 'expo-router';
import { useTranslation } from 'react-i18next';
import { SafeAreaView } from 'react-native-safe-area-context';

import type { AssistantAction, ChatMessage } from '@/api/contracts';
import { Banner, Button, Card, Chip, Icon, Text } from '@/components/ui';
import { SUPPORTED_LANGUAGES } from '@/i18n';
import { speak, stopSpeaking } from '@/features/voice/textToSpeech';
import { useAssistant } from '@/hooks/useAssistant';
import { useCanSpeak } from '@/hooks/useCanSpeak';
import { useSpeechInput } from '@/hooks/useSpeechInput';
import { useAppStore } from '@/store/useAppStore';
import { colors, radius, spacing, typography, MIN_TOUCH_SIZE } from '@/theme';

/**
 * Multilingual AI assistant.
 *
 * Runs the same voice pipeline as app/voice.tsx, wired for conversation rather
 * than a single question:
 *
 *   mic → Speech-to-Text → COMPOSER → send → ChatResponse → Text-to-Speech
 *
 * Two deliberate differences from the voice screen:
 *
 *  1. The transcript lands in the composer instead of sending itself. This is a
 *     multi-turn conversation with an edit field already on screen, so a
 *     misheard question about a loan is worth one tap to fix. The voice screen
 *     sends immediately because waiting for a second tap would defeat it.
 *  2. Replies are spoken automatically ONLY when the question was spoken. Someone
 *     who talked to the app probably cannot comfortably read the answer; someone
 *     who typed it has the "Read aloud" button and does not need audio starting
 *     unbidden.
 *
 * The mic is rendered only when `capability.available`. Where speech is
 * unavailable it is absent rather than dead — ADR-010, ADR-019 — and typing,
 * which is the primary affordance here anyway, still works. The voice screen is
 * where the reason gets explained, because there it is the whole feature.
 */

/**
 * Starter chips for the empty state. The strings live in i18n, not in the mock
 * fixture they used to come from — a screen must never import from `api/mock/`.
 *
 * The direct benefit was the language gap: the fixture carried only `en` and
 * `hi`, so the first thing a Marathi, Bengali, Tamil or Telugu user saw on this
 * screen was five English chips. All six now come from the locale files.
 *
 * (It does NOT change what ships. The service layer statically imports
 * `api/mock/server`, so Metro bundles the fixtures either way — see
 * docs/BACKEND_HANDOFF.md § What still ships in backend mode.)
 */
const STARTER_PROMPT_KEYS = ['p1', 'p2', 'p3', 'p4', 'p5'] as const;
export default function AssistantScreen() {
  const { t } = useTranslation();
  const language = useAppStore((s) => s.language);
  const { messages, isThinking, send, clear } = useAssistant(language);
  const [input, setInput] = useState('');
  /** True while the composer holds a transcript rather than typed text. */
  const [inputFromSpeech, setInputFromSpeech] = useState(false);
  const [speakingId, setSpeakingId] = useState<string | null>(null);
  const [actions, setActions] = useState<AssistantAction[]>([]);
  const [followUps, setFollowUps] = useState<string[]>([]);
  const scrollRef = useRef<ScrollView>(null);
  // Whether the turn in flight arrived by voice, which decides whether the
  // reply reads itself aloud. A ref, not state: it must be readable inside the
  // await below without re-rendering the conversation mid-request.
  const askedByVoice = useRef(false);
  // False when the device has no voice for this language — speaking then would
  // read the script with another language's phonetics and report success.
  const canRead = useCanSpeak(language);

  const submit = async (text: string, viaVoice = false) => {
    askedByVoice.current = viaVoice;
    setInput('');
    setInputFromSpeech(false);
    setActions([]);
    setFollowUps([]);
    const response = await send(text);
    if (response) {
      setActions(response.suggestedActions);
      setFollowUps(response.followUpQuestions);
      if (askedByVoice.current && canRead) {
        setSpeakingId(response.messageId);
        speak(response.answer, response.answerLanguage, {
          onDone: () => setSpeakingId(null),
        });
      }
    }
    setTimeout(() => scrollRef.current?.scrollToEnd({ animated: true }), 100);
  };

  const speech = useSpeechInput(language, {
    // Interim results stream into the composer so the user watches it hear them.
    onPartial: (text) => {
      setInput(text);
      setInputFromSpeech(true);
    },
    onFinal: (text) => {
      setInput(text);
      setInputFromSpeech(true);
    },
  });

  const toggleSpeech = (message: ChatMessage) => {
    if (speakingId === message.id) {
      stopSpeaking();
      setSpeakingId(null);
      return;
    }
    setSpeakingId(message.id);
    speak(message.content, message.language ?? language, {
      onDone: () => setSpeakingId(null),
    });
  };

  const runAction = (action: AssistantAction) => {
    switch (action.type) {
      case 'OPEN_SCHEME':
        router.push(`/scheme/${action.schemeId}`);
        break;
      case 'OPEN_PARTNER':
        router.push('/(tabs)/partners');
        break;
      case 'OPEN_CALCULATOR':
        router.push({
          pathname: '/(tabs)/calculator',
          params: {
            ...(action.principal ? { principal: action.principal } : {}),
            ...(action.annualRatePct ? { rate: action.annualRatePct } : {}),
            ...(action.tenureMonths ? { tenure: action.tenureMonths } : {}),
          },
        });
        break;
      case 'START_RECOMMENDER':
        router.push('/recommend');
        break;
      case 'OPEN_URL':
        break;
    }
  };

  return (
    <SafeAreaView style={styles.safe} edges={['bottom']}>
      <KeyboardAvoidingView
        style={styles.flex}
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
        keyboardVerticalOffset={90}
      >
        <ScrollView
          ref={scrollRef}
          style={styles.flex}
          contentContainerStyle={styles.scroll}
          keyboardShouldPersistTaps="handled"
        >
          {messages.length === 0 ? (
            <View style={styles.empty}>
              <View style={styles.emptyBadge}>
                <Icon name="chat" size={30} color={colors.textInverse} strokeWidth={1.8} />
              </View>
              <Text variant="title" center>
                {t('assistant.emptyTitle')}
              </Text>
              {/* Each language in its own script — the clearest way to say
                  "you may write in yours" to someone who cannot read English. */}
              <Text variant="body" color={colors.textSecondary} center>
                {t('assistant.emptyBody')} {SUPPORTED_LANGUAGES.map((l) => l.endonym).join(', ')}.
              </Text>

              <Text variant="label" color={colors.textMuted} style={styles.suggestLabel}>
                {t('assistant.suggestedTitle')}
              </Text>
              <View style={styles.suggestions}>
                {STARTER_PROMPT_KEYS.map((key) => {
                  const label = t(`assistant.prompts.${key}`);
                  return (
                    <Chip
                      key={key}
                      label={label}
                      tone="primary"
                      onPress={() => void submit(label)}
                    />
                  );
                })}
              </View>
            </View>
          ) : null}

          {messages.map((message) =>
            message.role === 'user' ? (
              <View key={message.id} style={styles.userBubble}>
                <Text variant="body" color={colors.textInverse}>
                  {message.content}
                </Text>
              </View>
            ) : (
              <View key={message.id} style={styles.assistantBlock}>
                {message.error ? (
                  <Banner tone="danger" message={t('assistant.retryMessage')} />
                ) : (
                  <Card>
                    <Text variant="body">{message.content}</Text>

                    {message.citations.length > 0 ? (
                      <View style={styles.citations}>
                        <Text variant="label" color={colors.textMuted}>
                          {t('assistant.sources')}
                        </Text>
                        {message.citations.map((citation) => (
                          <Text key={citation.id} variant="caption" color={colors.textSecondary}>
                            • {citation.title}
                            {citation.locator ? ` — ${citation.locator}` : ''}
                          </Text>
                        ))}
                      </View>
                    ) : (
                      <Text variant="caption" color={colors.textMuted} style={styles.citations}>
                        {t('assistant.noSources')}
                      </Text>
                    )}

                    {canRead ? (
                      <Button
                        title={
                          speakingId === message.id
                            ? t('assistant.stopReading')
                            : t('assistant.readAloud')
                        }
                        variant="ghost"
                        size="sm"
                        fullWidth={false}
                        style={styles.speakBtn}
                        onPress={() => toggleSpeech(message)}
                      />
                    ) : null}
                  </Card>
                )}
              </View>
            ),
          )}

          {isThinking ? (
            <View style={styles.thinking}>
              <ActivityIndicator color={colors.primary} />
              <Text variant="caption" color={colors.textMuted}>
                {t('assistant.thinking')}
              </Text>
            </View>
          ) : null}

          {actions.length > 0 ? (
            <View style={styles.actionRow}>
              {actions.map((action, index) => (
                <Chip
                  key={`${action.type}-${index}`}
                  label={action.label}
                  tone="info"
                  onPress={() => runAction(action)}
                />
              ))}
            </View>
          ) : null}

          {followUps.length > 0 ? (
            <View style={styles.followUps}>
              <Text variant="label" color={colors.textMuted}>
                {t('assistant.followUps')}
              </Text>
              <View style={styles.actionRow}>
                {followUps.map((question) => (
                  <Chip
                    key={question}
                    label={question}
                    tone="neutral"
                    onPress={() => void submit(question)}
                  />
                ))}
              </View>
            </View>
          ) : null}

          {messages.length > 0 ? (
            <Button
              title={t('assistant.clearChat')}
              variant="ghost"
              size="sm"
              onPress={() => {
                stopSpeaking();
                speech.cancel();
                setSpeakingId(null);
                clear();
                setActions([]);
                setFollowUps([]);
              }}
            />
          ) : null}
        </ScrollView>

        {speech.error ? (
          <View style={styles.speechError}>
            <Banner
              tone="warning"
              message={t(`voice.error.${speech.error}`, { code: speech.errorCode ?? '?' })}
            />
          </View>
        ) : null}

        <View style={styles.composer}>
          <TextInput
            value={input}
            onChangeText={setInput}
            placeholder={speech.isListening ? t('assistant.listening') : t('assistant.placeholder')}
            placeholderTextColor={colors.textMuted}
            style={styles.input}
            multiline
            accessibilityLabel={t('assistant.placeholder')}
            onSubmitEditing={() => void submit(input)}
          />

          {/* Absent, not dead, where speech is unavailable — see the note above. */}
          {speech.capability.available ? (
            <Pressable
              accessibilityRole="button"
              accessibilityLabel={
                speech.isListening ? t('voice.action.listening') : t('assistant.speak')
              }
              accessibilityState={{ selected: speech.isListening }}
              onPress={speech.toggle}
              style={({ pressed }) => [
                styles.micBtn,
                speech.isListening && styles.micListening,
                pressed && styles.pressed,
              ]}
            >
              <Icon
                name="mic"
                size={20}
                color={speech.isListening ? colors.textInverse : colors.primary}
                strokeWidth={2}
              />
            </Pressable>
          ) : null}

          <Pressable
            accessibilityRole="button"
            accessibilityLabel={t('assistant.send')}
            disabled={!input.trim() || isThinking}
            // A question that arrived by voice gets answered by voice. Editing a
            // transcript keeps the flag — someone who spoke because they cannot read
            // still cannot read after fixing one word. submit() clears it, so typing
            // a fresh question afterwards is treated as typed.
            onPress={() => void submit(input, inputFromSpeech)}
            style={({ pressed }) => [
              styles.sendBtn,
              (!input.trim() || isThinking) && styles.sendDisabled,
              pressed && styles.pressed,
            ]}
          >
            <Icon name="send" size={20} color={colors.textInverse} strokeWidth={2} />
          </Pressable>
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  flex: { flex: 1 },
  scroll: { padding: spacing.lg, gap: spacing.md, paddingBottom: spacing.xl },
  empty: { alignItems: 'center', gap: spacing.sm, marginTop: spacing.xl },
  emptyBadge: {
    width: 60,
    height: 60,
    borderRadius: radius.lg,
    backgroundColor: colors.inverse,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: spacing.sm,
  },
  suggestLabel: { marginTop: spacing.lg },
  suggestions: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.sm,
    justifyContent: 'center',
  },
  userBubble: {
    alignSelf: 'flex-end',
    maxWidth: '85%',
    backgroundColor: colors.primary,
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.md,
    borderRadius: radius.lg,
    borderBottomRightRadius: radius.sm,
  },
  assistantBlock: { alignSelf: 'stretch' },
  citations: { gap: 2, marginTop: spacing.md },
  speakBtn: { alignSelf: 'flex-start', marginTop: spacing.sm, paddingHorizontal: 0 },
  thinking: { flexDirection: 'row', alignItems: 'center', gap: spacing.sm },
  actionRow: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.sm },
  followUps: { gap: spacing.sm },
  composer: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    gap: spacing.sm,
    padding: spacing.md,
    borderTopWidth: 1,
    borderTopColor: colors.border,
    backgroundColor: colors.surface,
  },
  input: {
    flex: 1,
    ...typography.body,
    color: colors.text,
    maxHeight: 120,
    minHeight: MIN_TOUCH_SIZE,
    backgroundColor: colors.background,
    borderWidth: 1.5,
    borderColor: colors.border,
    borderRadius: radius.lg,
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.md,
    paddingBottom: spacing.md,
  },
  sendBtn: {
    width: MIN_TOUCH_SIZE,
    height: MIN_TOUCH_SIZE,
    borderRadius: radius.lg,
    backgroundColor: colors.primary,
    alignItems: 'center',
    justifyContent: 'center',
  },
  sendDisabled: { opacity: 0.4 },
  micBtn: {
    width: MIN_TOUCH_SIZE,
    height: MIN_TOUCH_SIZE,
    borderRadius: radius.lg,
    borderWidth: 1.5,
    borderColor: colors.border,
    backgroundColor: colors.surface,
    alignItems: 'center',
    justifyContent: 'center',
  },
  // Listening is signalled by fill AND by the placeholder changing to
  // "Listening…", never by colour alone.
  micListening: { backgroundColor: colors.danger, borderColor: colors.danger },
  speechError: { paddingHorizontal: spacing.md, paddingBottom: spacing.sm },
  pressed: { opacity: 0.85 },
});
