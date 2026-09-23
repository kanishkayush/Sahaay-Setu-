import { useState, useEffect } from 'react';
import { StyleSheet, View } from 'react-native';
import { router } from 'expo-router';
import { useTranslation } from 'react-i18next';

import type { ApplicantProfile, EducationStatus, ProjectType } from '@/api/contracts';
import { AmountInput, Button, OptionList, Screen, Text } from '@/components/ui';
import { useAppStore } from '@/store/useAppStore';
import { colors, radius, spacing } from '@/theme';

/**
 * Smart Scheme Recommender — the input wizard.
 *
 * One question per screen, deliberately. A single long form is intimidating and
 * has far worse completion rates with first-time smartphone users; a wizard also
 * lets us keep every touch target large and every question in plain language.
 *
 * The four questions map exactly to the inputs named in the problem statement:
 * project type, estimated cost, income level, education status. Gender is a
 * fifth, optional step because several schemes give women a lower rate.
 */

const PROJECT_TYPES: ProjectType[] = [
  'RETAIL_SHOP',
  'AGRICULTURE',
  'ANIMAL_HUSBANDRY',
  'ARTISAN_CRAFT',
  'SERVICES',
  'SMALL_MANUFACTURING',
  'TRANSPORT_VEHICLE',
  'EDUCATION',
  'OTHER',
];

const EDUCATION_LEVELS: EducationStatus[] = [
  'NONE',
  'PRIMARY',
  'SECONDARY',
  'HIGHER_SECONDARY',
  'VOCATIONAL',
  'GRADUATE',
  'POSTGRADUATE',
];

const COST_PRESETS = [50_000, 140_000, 500_000, 2_000_000];
const INCOME_PRESETS = [60_000, 120_000, 250_000, 500_000];

const TOTAL_STEPS = 5;

export default function RecommendWizard() {
  const { t } = useTranslation();
  const savedProfile = useAppStore((s) => s.profile);
  const setProfile = useAppStore((s) => s.setProfile);

  const [step, setStep] = useState(0);
  const [projectType, setProjectType] = useState<ProjectType | undefined>(
    savedProfile?.projectType,
  );
  const [projectCost, setProjectCost] = useState(savedProfile?.estimatedProjectCost ?? 0);
  const [income, setIncome] = useState(savedProfile?.annualFamilyIncome ?? 0);
  const [education, setEducation] = useState<EducationStatus | undefined>(
    savedProfile?.educationStatus,
  );
  const [gender, setGender] = useState<ApplicantProfile['gender']>(savedProfile?.gender);

  useEffect(() => {
    if (!savedProfile) {
      setStep(0);
      setProjectType(undefined);
      setProjectCost(0);
      setIncome(0);
      setEducation(undefined);
      setGender(undefined);
    }
  }, [savedProfile]);

  const canAdvance = [
    Boolean(projectType),
    projectCost > 0,
    income > 0,
    Boolean(education),
    true, // gender is optional
  ][step];

  const submit = () => {
    if (!projectType || !education) return;
    const profile: ApplicantProfile = {
      projectType,
      estimatedProjectCost: projectCost,
      annualFamilyIncome: income,
      educationStatus: education,
      gender,
    };
    setProfile(profile);
    router.push('/recommend/results');
  };

  return (
    <Screen
      edges={['bottom']}
      footer={
        <View style={styles.footer}>
          <Button
            title={step === TOTAL_STEPS - 1 ? t('recommender.submit') : t('common.next')}
            disabled={!canAdvance}
            onPress={() => (step === TOTAL_STEPS - 1 ? submit() : setStep((s) => s + 1))}
          />
          {step > 0 ? (
            <Button
              title={t('common.back')}
              variant="ghost"
              size="sm"
              onPress={() => setStep((s) => s - 1)}
            />
          ) : null}
        </View>
      }
    >
      {/* One dash per question, from the Open Design iOS sheet. A segmented bar
          shows how many steps remain; a continuous one only shows a fraction. */}
      <View style={styles.progressWrap}>
        <View style={styles.segments}>
          {Array.from({ length: TOTAL_STEPS }, (_, i) => (
            <View key={i} style={[styles.segment, i <= step && styles.segmentDone]} />
          ))}
        </View>
        <Text variant="label" color={colors.textMuted} style={styles.stepLabel}>
          {t('recommender.stepOf', { current: step + 1, total: TOTAL_STEPS })}
        </Text>
      </View>

      {step === 0 ? (
        <View style={styles.stepBody}>
          <Text variant="title">{t('recommender.projectTypeQuestion')}</Text>
          <OptionList
            options={PROJECT_TYPES.map((value) => ({
              value,
              label: t(`projectType.${value}`),
            }))}
            value={projectType}
            onChange={setProjectType}
          />
        </View>
      ) : null}

      {step === 1 ? (
        <View style={styles.stepBody}>
          <Text variant="title">{t('recommender.projectCostQuestion')}</Text>
          <AmountInput
            label={t('recommender.projectCostQuestion')}
            hint={t('recommender.projectCostHint')}
            value={projectCost}
            onChange={setProjectCost}
            presets={COST_PRESETS}
            max={50_000_000}
          />
        </View>
      ) : null}

      {step === 2 ? (
        <View style={styles.stepBody}>
          <Text variant="title">{t('recommender.incomeQuestion')}</Text>
          <AmountInput
            label={t('recommender.incomeQuestion')}
            hint={t('recommender.incomeHint')}
            value={income}
            onChange={setIncome}
            presets={INCOME_PRESETS}
            max={10_000_000}
          />
        </View>
      ) : null}

      {step === 3 ? (
        <View style={styles.stepBody}>
          <Text variant="title">{t('recommender.educationQuestion')}</Text>
          <OptionList
            options={EDUCATION_LEVELS.map((level) => ({
              value: level,
              label: t(`education.${level}`),
            }))}
            value={education}
            onChange={setEducation}
          />
        </View>
      ) : null}

      {step === 4 ? (
        <View style={styles.stepBody}>
          <Text variant="title">{t('recommender.genderQuestion')}</Text>
          <Text variant="caption" color={colors.textMuted}>
            {t('recommender.genderHint')}
          </Text>
          <OptionList
            options={[
              { value: 'FEMALE' as const, label: t('gender.FEMALE') },
              { value: 'MALE' as const, label: t('gender.MALE') },
              { value: 'OTHER' as const, label: t('gender.OTHER') },
            ]}
            value={gender}
            onChange={setGender}
          />
        </View>
      ) : null}
    </Screen>
  );
}

const styles = StyleSheet.create({
  progressWrap: { gap: spacing.md, marginTop: spacing.md },
  segments: { flexDirection: 'row', gap: 6 },
  segment: {
    flex: 1,
    height: 5,
    borderRadius: radius.pill,
    backgroundColor: colors.borderSoft,
  },
  segmentDone: { backgroundColor: colors.inverse },
  stepLabel: { textTransform: 'uppercase' },
  stepBody: { gap: spacing.lg },
  footer: { gap: spacing.sm },
});
