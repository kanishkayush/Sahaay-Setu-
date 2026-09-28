import React, { useState } from 'react';
import { View, StyleSheet, TextInput, Alert, type KeyboardTypeOptions } from 'react-native';
import { useTranslation } from 'react-i18next';

import { colors, radius, spacing } from '../../../src/theme';
import { Text } from '../../components/ui/Text';
import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';
import { Chip } from '../../components/ui/Chip';
import { ProfileUpdateRequest, UserProfile } from '../../../src/api/contracts/profile';

interface EditProfileFormProps {
  initialData: UserProfile;
  onSave: (data: ProfileUpdateRequest) => void;
  onCancel: () => void;
  isSaving: boolean;
}

/**
 * Stable module-scope input. Defining this inside EditProfileForm recreates the
 * component type on every keystroke, remounts TextInput, and accepts only one
 * character before focus is lost.
 */
function ProfileTextField({
  label,
  value,
  onChangeText,
  keyboardType = 'default',
  testID,
}: {
  label: string;
  value: string;
  onChangeText: (text: string) => void;
  keyboardType?: KeyboardTypeOptions;
  testID?: string;
}) {
  return (
    <View style={styles.inputContainer}>
      <Text variant="caption" color={colors.textMuted} style={styles.inputLabel}>{label}</Text>
      <TextInput
        testID={testID}
        style={styles.input}
        value={value}
        onChangeText={onChangeText}
        keyboardType={keyboardType}
        placeholderTextColor={colors.textMuted}
        autoCorrect={false}
      />
    </View>
  );
}

export function EditProfileForm({ initialData, onSave, onCancel, isSaving }: EditProfileFormProps) {
  const { t } = useTranslation();

  // Local edit state only. Server profile is applied on mount / when the user
  // re-enters edit mode, never on each keystroke.
  const [fullName, setFullName] = useState(initialData.fullName || '');
  const [phoneNumber, setPhoneNumber] = useState(initialData.phoneNumber || '');
  const [email, setEmail] = useState(initialData.email || '');
  const [dateOfBirth, setDateOfBirth] = useState(initialData.dateOfBirth || '');

  const [pinCode, setPinCode] = useState(initialData.address?.pinCode || '');
  const [stateName, setStateName] = useState(initialData.address?.state || '');
  const [district, setDistrict] = useState(initialData.address?.district || '');
  const [city, setCity] = useState(initialData.address?.city || '');
  const [addressLine1, setAddressLine1] = useState(initialData.address?.addressLine1 || '');

  const [educationLevel, setEducationLevel] = useState(initialData.educationLevel || '');
  const [occupation, setOccupation] = useState(initialData.occupation || '');
  const [annualFamilyIncome, setAnnualFamilyIncome] = useState(
    initialData.eligibility?.annualFamilyIncome?.toString() || ''
  );
  const [scEligibilityStatus, setScEligibilityStatus] = useState<boolean | null>(
    initialData.eligibility?.scEligibilityStatus ?? null
  );

  const [existingBusiness, setExistingBusiness] = useState<boolean | null>(
    initialData.business?.existingBusiness ?? null
  );
  const [businessActivity, setBusinessActivity] = useState(initialData.business?.businessActivity || '');

  const handleSave = () => {
    if (pinCode && !/^\d{6}$/.test(pinCode)) {
      Alert.alert(t('profile.invalidPin', 'Invalid PIN Code'), t('profile.invalidPinMsg', 'Please enter a valid 6-digit PIN code.'));
      return;
    }

    const payload: ProfileUpdateRequest = {
      fullName: fullName || undefined,
      phoneNumber: phoneNumber || undefined,
      email: email || undefined,
      dateOfBirth: dateOfBirth || undefined,
      educationLevel: educationLevel || undefined,
      occupation: occupation || undefined,
      address: {
        pinCode: pinCode || undefined,
        state: stateName || undefined,
        district: district || undefined,
        city: city || undefined,
        addressLine1: addressLine1 || undefined,
        coordinates: initialData.address?.coordinates,
      },
      eligibility: {
        annualFamilyIncome: annualFamilyIncome ? parseInt(annualFamilyIncome, 10) : undefined,
        scEligibilityStatus: scEligibilityStatus,
      },
      business: {
        existingBusiness,
        businessActivity: businessActivity || undefined,
      },
    };
    onSave(payload);
  };

  return (
    <View style={styles.container}>
      <Text variant="subheading" style={styles.sectionTitle}>{t('profile.personalDetails', 'Personal Details')}</Text>
      <Card variant="glass">
        <ProfileTextField testID="profile-fullName" label={t('profile.fullName', 'Full Name')} value={fullName} onChangeText={setFullName} />
        <ProfileTextField testID="profile-phoneNumber" label={t('profile.phoneNumber', 'Mobile Number')} value={phoneNumber} onChangeText={setPhoneNumber} keyboardType="phone-pad" />
        <ProfileTextField testID="profile-email" label={t('profile.email', 'Email Address')} value={email} onChangeText={setEmail} keyboardType="email-address" />
        <ProfileTextField testID="profile-dateOfBirth" label={t('profile.dateOfBirth', 'Date of Birth (YYYY-MM-DD)')} value={dateOfBirth} onChangeText={setDateOfBirth} />
      </Card>

      <Text variant="subheading" style={styles.sectionTitle}>{t('profile.addressDetails', 'Address Details')}</Text>
      <Card variant="glass">
        <ProfileTextField testID="profile-pinCode" label={t('profile.pinCode', 'PIN Code')} value={pinCode} onChangeText={setPinCode} keyboardType="number-pad" />
        <ProfileTextField testID="profile-state" label={t('profile.state', 'State')} value={stateName} onChangeText={setStateName} />
        <ProfileTextField testID="profile-district" label={t('profile.district', 'District')} value={district} onChangeText={setDistrict} />
        <ProfileTextField testID="profile-city" label={t('profile.city', 'City')} value={city} onChangeText={setCity} />
        <ProfileTextField testID="profile-addressLine1" label={t('profile.addressLine1', 'Address Line 1')} value={addressLine1} onChangeText={setAddressLine1} />
      </Card>

      <Text variant="subheading" style={styles.sectionTitle}>{t('profile.educationAndEligibility', 'Education & Eligibility Details')}</Text>
      <Card variant="glass">
        <ProfileTextField testID="profile-educationLevel" label={t('profile.educationLevel', 'Education Level')} value={educationLevel} onChangeText={setEducationLevel} />
        <ProfileTextField testID="profile-occupation" label={t('profile.occupation', 'Occupation')} value={occupation} onChangeText={setOccupation} />
        <ProfileTextField testID="profile-annualFamilyIncome" label={t('profile.annualFamilyIncome', 'Annual Family Income (₹)')} value={annualFamilyIncome} onChangeText={setAnnualFamilyIncome} keyboardType="number-pad" />

        <View style={styles.switchContainer}>
          <Text variant="body" style={{ flex: 1 }}>{t('profile.scEligibility', 'SC Category Eligibility')}</Text>
        </View>
        <View style={styles.triRow}>
          <Chip label={t('profile.notProvided', 'Not provided')} selected={scEligibilityStatus === null} onPress={() => setScEligibilityStatus(null)} tone="neutral" />
          <Chip label={t('common.yes', 'Yes')} selected={scEligibilityStatus === true} onPress={() => setScEligibilityStatus(true)} tone="primary" />
          <Chip label={t('common.no', 'No')} selected={scEligibilityStatus === false} onPress={() => setScEligibilityStatus(false)} tone="primary" />
        </View>
      </Card>

      <Text variant="subheading" style={styles.sectionTitle}>{t('profile.businessDetails', 'Business Details')}</Text>
      <Card variant="glass">
        <View style={styles.switchContainer}>
          <Text variant="body" style={{ flex: 1 }}>{t('profile.existingBusiness', 'Has Existing Business?')}</Text>
        </View>
        <View style={styles.triRow}>
          <Chip label={t('profile.notProvided', 'Not provided')} selected={existingBusiness === null} onPress={() => setExistingBusiness(null)} tone="neutral" />
          <Chip label={t('common.yes', 'Yes')} selected={existingBusiness === true} onPress={() => setExistingBusiness(true)} tone="primary" />
          <Chip label={t('common.no', 'No')} selected={existingBusiness === false} onPress={() => setExistingBusiness(false)} tone="primary" />
        </View>
        {existingBusiness === true && (
          <ProfileTextField testID="profile-businessActivity" label={t('profile.businessActivity', 'Business Activity')} value={businessActivity} onChangeText={setBusinessActivity} />
        )}
      </Card>

      <View style={styles.actions}>
        <Button
          title={t('profile.cancel', 'Cancel')}
          variant="outline"
          onPress={onCancel}
          disabled={isSaving}
          style={{ flex: 1 }}
        />
        <Button
          title={isSaving ? t('profile.saving', 'Saving...') : t('profile.saveDetails', 'Save Profile Details')}
          variant="primary"
          onPress={handleSave}
          disabled={isSaving}
          loading={isSaving}
          style={{ flex: 1 }}
        />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    gap: spacing.md,
    paddingBottom: spacing.xl,
  },
  sectionTitle: {
    marginTop: spacing.sm,
    marginBottom: spacing.xs,
  },
  inputContainer: {
    marginBottom: spacing.md,
  },
  inputLabel: {
    marginBottom: spacing.xs,
  },
  input: {
    borderWidth: 1.5,
    borderColor: colors.borderStrong,
    borderRadius: radius.md,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    color: colors.text,
    fontSize: 16,
    backgroundColor: colors.surface,
  },
  triRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.sm,
    marginBottom: spacing.md,
  },
  switchContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: spacing.sm,
  },
  actions: {
    flexDirection: 'row',
    gap: spacing.md,
    marginTop: spacing.md,
  },
});
