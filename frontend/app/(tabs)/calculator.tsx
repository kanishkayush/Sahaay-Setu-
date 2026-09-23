import { useMemo, useState } from 'react';
import { StyleSheet, View, Platform } from 'react-native';
import { useLocalSearchParams } from 'expo-router';
import { useTranslation } from 'react-i18next';

import {
  AmountInput,
  Banner,
  Button,
  Card,
  Chip,
  ResultCard,
  Screen,
  Stepper,
  Text,
} from '@/components/ui';
import { calculateEmi, type MoratoriumTreatment } from '@/features/calculator/emi';
import { scheduleReminders, type ReminderSchedule } from '@/features/calculator/notifications';
import { useAppStore } from '@/store/useAppStore';
import { colors, spacing } from '@/theme';
import { formatCurrency, formatMonths, formatPercent, formatStatCurrency } from '@/utils/format';

const LOAN_PRESETS = [50_000, 140_000, 500_000, 2_000_000];

/**
 * Financial Calculator.
 *
 * Accepts deep-link params so a scheme page or the AI assistant can open it
 * pre-filled: /calculator?principal=200000&rate=6.5&tenure=60&moratorium=6
 *
 * Also reads from loanJourney store so the Guided Journey amount persists
 * across navigation without requiring deep-link params.
 *
 * IMPORTANT: Repayment reminders are only scheduled when loanStatus === 'DISBURSED'.
 * Before that, the schedule is shown as ESTIMATES only.
 */
export default function CalculatorScreen() {
  const { t } = useTranslation();
  const params = useLocalSearchParams<{
    principal?: string;
    rate?: string;
    tenure?: string;
    moratorium?: string;
    scheme?: string;
  }>();

  const loanJourney = useAppStore((s) => s.loanJourney);

  // Priority: URL param → loan journey store → hardcoded default
  const defaultPrincipal =
    Number(params.principal) ||
    loanJourney.requestedLoanAmount ||
    140_000;


  const [principal, setPrincipal] = useState(() => defaultPrincipal);
  const [rate, setRate] = useState(() => Number(params.rate) || loanJourney.interestRate || 6.5);
  const [tenure, setTenure] = useState(() => Number(params.tenure) || loanJourney.tenureMonths || 60);
  const [moratorium, setMoratorium] = useState(() => Number(params.moratorium) || 6);
  const [treatment, setTreatment] = useState<MoratoriumTreatment>('CAPITALISE');
  const [showSchedule, setShowSchedule] = useState(false);
  const [simulatedReminders, setSimulatedReminders] = useState<ReminderSchedule[]>([]);
  const [scheduling, setScheduling] = useState(false);

  const isDisbursed = loanJourney.loanStatus === 'DISBURSED';
  const hasPartner = loanJourney.loanStatus === 'PARTNER_SELECTED' || loanJourney.loanStatus === 'APPLICATION_SUBMITTED' || loanJourney.loanStatus === 'APPROVED' || isDisbursed;
  const fromJourney = !!loanJourney.requestedLoanAmount;

  const handleScheduleReminders = async () => {
    if (!result) return;
    setScheduling(true);
    setSimulatedReminders([]);

    const reminders: ReminderSchedule[] = [];
    const today = new Date();

    // Schedule for the first 3 EMIs for demonstration
    const emiMonths = result.schedule.filter(s => !s.isMoratorium).slice(0, 3);
    
    emiMonths.forEach((row, i) => {
      // Use exact due date computed in EMI calculator
      const dueDate = new Date(row.dueDate);
      
      // 7 days before
      const reminder7d = new Date(dueDate.getTime() - 7 * 24 * 60 * 60 * 1000);
      // 3 days before
      const reminder3d = new Date(dueDate.getTime() - 3 * 24 * 60 * 60 * 1000);
      // 1 day before
      const reminder1d = new Date(dueDate.getTime() - 1 * 24 * 60 * 60 * 1000);
      // On due date
      const reminder0d = new Date(dueDate.getTime());
      reminder0d.setHours(9, 0, 0, 0); // 9 AM
      reminder1d.setHours(9, 0, 0, 0);
      reminder3d.setHours(9, 0, 0, 0);
      reminder7d.setHours(9, 0, 0, 0);

      const emiAmt = formatCurrency(row.emi, false);
      const dateStr = dueDate.toLocaleDateString();

      reminders.push({
        id: `emi-${i}-7d`,
        title: `Upcoming EMI: ${emiAmt}`,
        body: `Your EMI is due on ${dateStr} (in 7 days).`,
        triggerDate: reminder7d,
      });
      reminders.push({
        id: `emi-${i}-3d`,
        title: `Upcoming EMI: ${emiAmt}`,
        body: `Your EMI is due on ${dateStr} (in 3 days).`,
        triggerDate: reminder3d,
      });
      reminders.push({
        id: `emi-${i}-1d`,
        title: `EMI Tomorrow: ${emiAmt}`,
        body: `Your EMI is due tomorrow (${dateStr}).`,
        triggerDate: reminder1d,
      });
      reminders.push({
        id: `emi-${i}-0d`,
        title: `EMI Due Today: ${emiAmt}`,
        body: `Your EMI is due today. Please ensure sufficient balance.`,
        triggerDate: reminder0d,
      });
    });

    const res = await scheduleReminders(reminders);
    if (res.success && Platform.OS === 'web') {
      setSimulatedReminders(res.scheduled);
    } else if (res.success) {
      alert("Reminders have been scheduled successfully.");
    } else {
      alert("Failed to schedule reminders: " + res.error);
    }
    setScheduling(false);
  };

  const result = useMemo(() => {
    if (principal <= 0) return null;
    return calculateEmi({
      principal,
      annualRatePct: rate,
      tenureMonths: tenure,
      moratoriumMonths: moratorium,
      moratoriumTreatment: treatment,
    });
  }, [principal, rate, tenure, moratorium, treatment]);

  const monthWord = t('common.months');
  const yearWord = t('common.years');

  return (
    <Screen>
      <View style={styles.header}>
        <Text variant="title">{t('calculator.title')}</Text>
        <Text variant="caption" color={colors.textSecondary}>
          {t('calculator.subtitle')}
        </Text>
      </View>

      {params.scheme ? (
        <Chip label={t('calculator.presetFromScheme', { scheme: params.scheme })} tone="info" />
      ) : null}

      {fromJourney ? (
        <Chip
          label={`Loan amount from Guided Journey: ${formatCurrency(loanJourney.requestedLoanAmount!)}`}
          tone="primary"
        />
      ) : null}

      {hasPartner && !isDisbursed ? (
        <Banner
          tone="warning"
          message={`⏳ Estimated repayment schedule. Final loan amount, interest rate, tenure and repayment dates will be confirmed after the loan is approved and disbursed by${loanJourney.selectedChannelPartnerName ? ` ${loanJourney.selectedChannelPartnerName}` : ' the channel partner'}.`}
        />
      ) : null}

      {isDisbursed && loanJourney.disbursementDate ? (
        <Banner
          tone="success"
          message={`✅ Loan disbursed on ${loanJourney.disbursementDate}. Your repayment schedule is now active.`}
        />
      ) : null}

      <AmountInput
        label={t('calculator.loanAmount')}
        value={principal}
        onChange={setPrincipal}
        presets={LOAN_PRESETS}
        max={50_000_000}
      />

      <Stepper
        label={t('calculator.interestRate')}
        value={rate}
        min={4}
        max={15}
        step={0.5}
        suffix={t('common.perYear')}
        format={(v) => formatPercent(v)}
        onChange={setRate}
        decreaseLabel={t('a11y.decrease')}
        increaseLabel={t('a11y.increase')}
      />

      <Stepper
        label={t('calculator.tenure')}
        value={tenure}
        min={6}
        max={120}
        step={6}
        format={(v) => formatMonths(v, monthWord, yearWord)}
        onChange={setTenure}
        decreaseLabel={t('a11y.decrease')}
        increaseLabel={t('a11y.increase')}
      />

      <Stepper
        label={t('calculator.moratorium')}
        hint={t('calculator.moratoriumHelp')}
        value={moratorium}
        min={0}
        max={12}
        step={1}
        suffix={monthWord}
        onChange={setMoratorium}
        decreaseLabel={t('a11y.decrease')}
        increaseLabel={t('a11y.increase')}
      />

      {moratorium > 0 ? (
        <View style={styles.treatment}>
          <Text variant="subheading">{t('calculator.treatment')}</Text>
          <View style={styles.treatmentRow}>
            <Chip
              label={t('calculator.capitalise')}
              tone="primary"
              selected={treatment === 'CAPITALISE'}
              onPress={() => setTreatment('CAPITALISE')}
            />
            <Chip
              label={t('calculator.serviceMonthly')}
              tone="primary"
              selected={treatment === 'SERVICE_MONTHLY'}
              onPress={() => setTreatment('SERVICE_MONTHLY')}
            />
          </View>
        </View>
      ) : null}

      {result ? (
        <>
          <ResultCard
            eyebrow={t('calculator.yourEmi')}
            value={formatCurrency(result.emi)}
            caption={
              moratorium > 0
                ? t('calculator.startsAfter', { months: moratorium })
                : t('calculator.startsImmediately')
            }
            footer={[
              {
                value: formatStatCurrency(result.totalPayable),
                label: t('calculator.totalPayable'),
              },
              {
                value: formatMonths(result.totalMonths, monthWord, yearWord),
                label: t('calculator.startToFinish'),
              },
            ]}
          />

          <Card>
            <Row label={t('calculator.principal')} value={formatCurrency(principal)} />
            {moratorium > 0 ? (
              <Row
                label={t('calculator.moratoriumInterest')}
                value={formatCurrency(result.moratoriumInterest)}
              />
            ) : null}
            <Row
              label={t('calculator.totalInterest')}
              value={formatCurrency(result.totalInterest)}
            />
            <Row
              label={t('calculator.totalMonths')}
              value={formatMonths(result.totalMonths, monthWord, yearWord)}
            />
            <Row
              label={t('calculator.totalPayable')}
              value={formatCurrency(result.totalPayable)}
              emphasis
              last
            />
          </Card>

          <Button
            title={showSchedule ? t('common.showLess') : t('calculator.viewSchedule')}
            variant="outline"
            onPress={() => setShowSchedule((s) => !s)}
          />

          {showSchedule && hasPartner && !isDisbursed ? (
            <Banner
              tone="info"
              message="Estimated dates only. Actual repayment dates start after loan disbursement."
            />
          ) : null}

          {showSchedule ? (
            <Card padded={false}>
              <View style={styles.tableHeader}>
                <Text variant="label" color={colors.textMuted} style={styles.colMonth}>
                  {t('calculator.date')}
                </Text>
                <Text variant="label" color={colors.textMuted} style={styles.col}>
                  {t('calculator.emi')}
                </Text>
                <Text variant="label" color={colors.textMuted} style={styles.col}>
                  {t('calculator.interest')}
                </Text>
                <Text variant="label" color={colors.textMuted} style={styles.col}>
                  {t('calculator.balance')}
                </Text>
              </View>
              {result.schedule.map((row) => (
                <View
                  key={row.month}
                  style={[styles.tableRow, row.isMoratorium && styles.moratoriumRow]}
                >
                  <Text variant="caption" style={styles.colMonth}>
                    {row.formattedDueDate}
                  </Text>
                  <Text variant="caption" style={styles.col}>
                    {formatCurrency(row.emi, false)}
                  </Text>
                  <Text variant="caption" style={styles.col}>
                    {formatCurrency(row.interestComponent, false)}
                  </Text>
                  <Text variant="caption" style={styles.col}>
                    {formatCurrency(row.closingBalance, false)}
                  </Text>
                </View>
              ))}
            </Card>
          ) : null}

          {isDisbursed ? (
            <Button
              title={scheduling ? 'Scheduling...' : 'Enable EMI Reminders'}
              variant="primary"
              onPress={handleScheduleReminders}
              disabled={scheduling}
              style={{ marginTop: spacing.md }}
            />
          ) : (
            <View style={{ marginTop: spacing.md }}>
              <Banner
                tone="info"
                message="🔔 Repayment reminders will become available after your loan is approved and disbursed."
              />
            </View>
          )}

          {simulatedReminders.length > 0 && Platform.OS === 'web' ? (
            <Card style={{ marginTop: spacing.md }}>
              <Text variant="subheading">Web Simulation: Scheduled Reminders</Text>
              <Text variant="caption" color={colors.textSecondary} style={{ marginBottom: spacing.sm }}>
                (On a real device, these would be scheduled in expo-notifications)
              </Text>
              {simulatedReminders.map((rem) => (
                <View key={rem.id} style={{ marginBottom: spacing.sm }}>
                  <Text variant="bodyStrong">✓ {rem.triggerDate.toLocaleDateString()} - {rem.title}</Text>
                  <Text variant="caption">{rem.body}</Text>
                </View>
              ))}
            </Card>
          ) : null}
        </>
      ) : null}

      <Banner tone="info" message={t('calculator.disclaimer')} />
    </Screen>
  );
}

function Row({
  label,
  value,
  emphasis,
  last,
}: {
  label: string;
  value: string;
  emphasis?: boolean;
  last?: boolean;
}) {
  return (
    <View style={[styles.row, !last && styles.rowBorder]}>
      <Text variant={emphasis ? 'bodyStrong' : 'body'} color={colors.textSecondary}>
        {label}
      </Text>
      <Text variant="bodyStrong" color={emphasis ? colors.primary : colors.text}>
        {value}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  header: { gap: spacing.xs, marginTop: spacing.md },
  treatment: { gap: spacing.sm },
  treatmentRow: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.sm },
  row: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    gap: spacing.md,
    paddingVertical: spacing.md,
  },
  rowBorder: { borderBottomWidth: 1, borderBottomColor: colors.border },
  tableHeader: {
    flexDirection: 'row',
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    backgroundColor: colors.surfaceAlt,
  },
  tableRow: {
    flexDirection: 'row',
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    borderTopWidth: 1,
    borderTopColor: colors.border,
  },
  moratoriumRow: { backgroundColor: colors.warningSurface },
  colMonth: { flex: 1.4 },
  col: { flex: 1, textAlign: 'right' },
});
