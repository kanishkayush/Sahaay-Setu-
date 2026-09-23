import { useState, useEffect, useRef } from 'react';
import { ActivityIndicator, Pressable, StyleSheet, TextInput, View } from 'react-native';
import { router } from 'expo-router';
import { useTranslation } from 'react-i18next';

import { Banner, Button, Card, Chip, Icon, Screen, Text } from '@/components/ui';
import { UICardsRenderer } from '@/components/domain/UICardsRenderer';
import type { AssistantAction } from '@/api/contracts';
import { useVoiceQuery, type VoicePhase } from '@/hooks/useVoiceQuery';
import { useAppStore } from '@/store/useAppStore';
import { colors, radius, spacing, MIN_TOUCH_SIZE } from '@/theme';

/**
 * Ask by voice.
 *
 * Voice pipeline lives in useVoiceQuery. When the Guided Journey expects
 * a PIN code (expectedField === 'pinCode'), we replace the mic with a
 * numeric keypad — PIN input should never rely on voice recognition.
 * After the PIN is submitted, voice mode resumes automatically.
 */

const MIC_SIZE = 128;

const PHASE_TONE: Record<VoicePhase, string> = {
  idle: colors.primary,
  listening: colors.danger,
  thinking: colors.textMuted,
  speaking: colors.success,
};

export default function VoiceScreen() {
  const { t } = useTranslation();
  const language = useAppStore((s) => s.language);
  const updateLoanJourney = useAppStore((s) => s.updateLoanJourney);
  const {
    capability,
    phase,
    transcript,
    turn,
    error,
    listen,
    stopListening,
    cancel,
    replay,
    askText,
    canSpeak,
    errorCode,
    clearLastResponse,
  } = useVoiceQuery(language);

  const [typed, setTyped] = useState('');
  const [pin, setPin] = useState('');
  const pinInputRef = useRef<TextInput>(null);
  const [recordingSeconds, setRecordingSeconds] = useState(0);

  // Derive input mode from the last backend response
  const inputMode = turn?.expectedField === 'pinCode' ? 'pin' : 'voice';

  useEffect(() => {
    let interval: ReturnType<typeof setInterval>;
    if (phase === 'listening') {
      setRecordingSeconds(0);
      interval = setInterval(() => {
        setRecordingSeconds((prev) => prev + 1);
      }, 1000);
    } else {
      setRecordingSeconds(0);
    }
    return () => clearInterval(interval);
  }, [phase]);

  // Ensure PIN input gets focus when it appears
  useEffect(() => {
    if (inputMode === 'pin') {
      // Small timeout to ensure the element is painted before focusing
      const timer = setTimeout(() => {
        pinInputRef.current?.focus();
      }, 100);
      return () => clearTimeout(timer);
    }
  }, [inputMode]);

  // When an OPEN_CALCULATOR action fires, save principal to loanJourney store.
  const handleAction = (action: AssistantAction) => {
    switch (action.type) {
      case 'OPEN_SCHEME':
        router.push(`/scheme/${action.schemeId}`);
        break;
      case 'OPEN_PARTNER':
        router.push('/(tabs)/partners');
        break;
      case 'OPEN_CALCULATOR':
        if (action.principal) {
          updateLoanJourney({
            requestedLoanAmount: action.principal,
            estimatedProjectCost: action.principal,
          });
        }
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

  const submitTyped = () => {
    const text = typed.trim();
    if (!text) return;
    setTyped('');
    void askText(text);
  };

  const submitPin = () => {
    if (!/^[1-9]\d{5}$/.test(pin)) return;
    const submittedPin = pin;
    setPin('');
    void askText(submittedPin);
  };

  const micPress = () => {
    if (phase === 'listening') stopListening();
    else if (phase === 'idle') listen();
    else cancel();
  };

  const isPinMode = inputMode === 'pin';

  return (
    <Screen>
      <View style={styles.header}>
        <Text variant="title">{t('voice.title')}</Text>
        <Text variant="body" color={colors.textSecondary}>
          {t('voice.subtitle')}
        </Text>
      </View>

      {!capability.available ? (
        <Banner tone="info" message={t(`voice.unavailable.${capability.reason}`)} />
      ) : null}

      {error === 'EMPTY_TRANSCRIPT' ? (
        <Banner tone="info" message={t('voice.emptyTranscript', 'Please speak or type your question first.')} />
      ) : error ? (
        <Banner tone="warning" message={t(`voice.error.${error}`, { code: errorCode ?? '?' })} />
      ) : null}

      {!canSpeak ? <Banner tone="info" message={t('voice.noVoice')} /> : null}

      {/* PIN mode: show numeric keypad instead of microphone */}
      {isPinMode ? (
        <View style={styles.pinArea}>
          <Text variant="subheading" center>
            {language === 'hi'
              ? 'अपना 6 अंकों का पिन कोड दर्ज करें'
              : 'Enter your 6-digit PIN code'}
          </Text>
          <Pressable onPress={() => pinInputRef.current?.focus()} style={{ alignItems: 'center' }}>
            <View style={styles.pinDisplayRow}>
              {[0, 1, 2, 3, 4, 5].map((i) => (
                <View key={i} style={[styles.pinDigitBox, pin[i] ? styles.pinDigitFilled : undefined]}>
                  <Text variant="subheading">{pin[i] ?? '–'}</Text>
                </View>
              ))}
            </View>
            <TextInput
              ref={pinInputRef}
              style={styles.pinHiddenInput}
              keyboardType="number-pad"
              maxLength={6}
              value={pin}
              onChangeText={(v) => {
                const digits = v.replace(/\D/g, '').slice(0, 6);
                setPin(digits);
              }}
              autoFocus
              accessibilityLabel={language === 'hi' ? 'पिन कोड' : 'PIN code'}
            />
          </Pressable>
          <Button
            title={language === 'hi' ? 'जारी रखें' : 'Continue'}
            variant="primary"
            disabled={!/^[1-9]\d{5}$/.test(pin) || phase === 'thinking'}
            onPress={submitPin}
            style={styles.pinSubmit}
          />
          {phase === 'thinking' ? (
            <ActivityIndicator color={colors.primary} />
          ) : null}
        </View>
      ) : null}

      {/* Voice mic — only shown when NOT in PIN mode */}
      {!isPinMode && capability.available ? (
        <View style={styles.micArea}>
          <Pressable
            accessibilityRole="button"
            accessibilityLabel={t(`voice.action.${phase}`)}
            accessibilityState={{ busy: phase === 'thinking' }}
            onPress={micPress}
            style={({ pressed }) => [
              styles.mic,
              { backgroundColor: PHASE_TONE[phase] },
              pressed && styles.pressed,
            ]}
          >
            {phase === 'thinking' ? (
              <ActivityIndicator size="large" color={colors.textInverse} />
            ) : (
              <Icon
                name={phase === 'speaking' ? 'speaker' : 'mic'}
                size={52}
                color={colors.textInverse}
                strokeWidth={1.8}
              />
            )}
          </Pressable>

          <Text variant="bodyStrong" color={colors.textSecondary}>
            {phase === 'listening' ? `${t(`voice.phase.${phase}`)} (${recordingSeconds}s)` : t(`voice.phase.${phase}`)}
          </Text>

          {phase !== 'idle' ? (
            <Button title={phase === 'listening' ? 'Stop Recording' : t('voice.cancel')} variant="outline" onPress={phase === 'listening' ? stopListening : cancel} />
          ) : null}
        </View>
      ) : null}

      {transcript ? (
        <Card>
          <Text variant="label" color={colors.textMuted}>
            {t('voice.youAsked')}
          </Text>
          <Text variant="body">{transcript}</Text>
        </Card>
      ) : null}

      {turn ? (
        <View style={styles.answer}>
          {!turn.grounded ? <Banner tone="warning" message={t('assistant.ungrounded')} /> : null}

          <Card>
            <Text variant="body">{turn.answer}</Text>

            {turn.citations.length > 0 ? (
              <View style={styles.citations}>
                <Text variant="label" color={colors.textMuted}>
                  {t('assistant.sources')}
                </Text>
                {turn.citations.map((c) => (
                  <Text key={c.id} variant="caption" color={colors.textSecondary}>
                    {c.title}
                    {c.locator ? ` — ${c.locator}` : ''}
                  </Text>
                ))}
              </View>
            ) : null}
          </Card>

          {turn.uiCards?.length > 0 ? (
            <UICardsRenderer
              cards={turn.uiCards}
              onOptionSelect={(opt) => void askText(opt)}
              onSelectPartner={(id, name) => {
                updateLoanJourney({
                  selectedChannelPartnerId: id,
                  selectedChannelPartnerName: name,
                  loanStatus: 'PARTNER_SELECTED',
                });
                router.push('/(tabs)/calculator');
              }}
            />
          ) : null}

          {canSpeak ? (
            <Button title={t('voice.replay')} variant="outline" onPress={replay} />
          ) : null}

          {turn.actions.length > 0 ? (
            <View style={styles.chips}>
              {turn.actions.map((action) => (
                <Chip
                  key={action.label}
                  label={action.label}
                  tone="primary"
                  onPress={() => handleAction(action)}
                />
              ))}
            </View>
          ) : null}

          <Button
            title="Clear Last Response"
            variant="ghost"
            size="sm"
            onPress={clearLastResponse}
          />

          {turn.followUps.length > 0 ? (
            <View style={styles.section}>
              <Text variant="label" color={colors.textMuted}>
                {t('voice.askNext')}
              </Text>
              <View style={styles.chips}>
                {turn.followUps.map((q) => (
                  <Chip key={q} label={q} tone="neutral" onPress={() => void askText(q)} />
                ))}
              </View>
            </View>
          ) : null}
        </View>
      ) : null}

      {/* Text input — always available, not only as fallback */}
      <View style={styles.section}>
        <Text variant="label" color={colors.textMuted}>
          {t('voice.orType')}
        </Text>
        <View style={styles.composer}>
          <TextInput
            value={typed}
            onChangeText={setTyped}
            placeholder={t('assistant.placeholder')}
            placeholderTextColor={colors.textMuted}
            style={styles.input}
            multiline
            accessibilityLabel={t('assistant.placeholder')}
            onSubmitEditing={submitTyped}
          />
          <Pressable
            accessibilityRole="button"
            accessibilityLabel={t('assistant.send')}
            disabled={!typed.trim() || phase === 'thinking'}
            onPress={submitTyped}
            style={({ pressed }) => [
              styles.send,
              (!typed.trim() || phase === 'thinking') && styles.sendDisabled,
              pressed && styles.pressed,
            ]}
          >
            <Icon name="send" size={20} color={colors.textInverse} strokeWidth={2} />
          </Pressable>
        </View>
      </View>

    </Screen>
  );
}

const styles = StyleSheet.create({
  header: { gap: spacing.xs, marginTop: spacing.md },
  micArea: { alignItems: 'center', gap: spacing.md, paddingVertical: spacing.xl },
  mic: {
    width: MIC_SIZE,
    height: MIC_SIZE,
    borderRadius: MIC_SIZE / 2,
    alignItems: 'center',
    justifyContent: 'center',
  },
  pressed: { opacity: 0.85 },
  answer: { gap: spacing.md },
  citations: { gap: spacing.xs, marginTop: spacing.sm },
  section: { gap: spacing.sm },
  chips: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.sm },
  composer: { flexDirection: 'row', gap: spacing.sm, alignItems: 'flex-end' },
  input: {
    flex: 1,
    minHeight: MIN_TOUCH_SIZE,
    maxHeight: 120,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.lg,
    paddingHorizontal: spacing.md,
    paddingTop: spacing.md,
    paddingBottom: spacing.md,
    backgroundColor: colors.surface,
    color: colors.text,
    fontSize: 17,
    lineHeight: 24,
  },
  send: {
    width: MIN_TOUCH_SIZE,
    height: MIN_TOUCH_SIZE,
    borderRadius: MIN_TOUCH_SIZE / 2,
    backgroundColor: colors.primary,
    alignItems: 'center',
    justifyContent: 'center',
  },
  sendDisabled: { backgroundColor: colors.borderStrong },
  // PIN mode styles
  pinArea: { gap: spacing.lg, paddingVertical: spacing.xl, alignItems: 'center' },
  pinDisplayRow: { flexDirection: 'row', gap: spacing.sm },
  pinDigitBox: {
    width: 44,
    height: 56,
    borderWidth: 2,
    borderColor: colors.border,
    borderRadius: radius.md,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: colors.surface,
  },
  pinDigitFilled: { borderColor: colors.primary },
  pinHiddenInput: {
    position: 'absolute',
    opacity: 0,
    width: 1,
    height: 1,
  },
  pinSubmit: { minWidth: 200 },
});
