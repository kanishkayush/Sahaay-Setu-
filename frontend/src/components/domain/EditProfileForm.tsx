import React, { useState } from 'react';
import { View, StyleSheet, TextInput, Switch, Alert } from 'react-native';
import { useTranslation } from 'react-i18next';

import { colors, radius, spacing } from '../../../src/theme';
import { Text } from '../../components/ui/Text';
import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';
import { ProfileUpdateRequest, UserProfile } from '../../../src/api/contracts/profile';

interface EditProfileFormProps {
  initialData: UserProfile;
  onSave: (data: ProfileUpdateRequest) => void;
  onCancel: () => void;
  isSaving: boolean;
}

export function EditProfileForm({ initialData, onSave, onCancel, isSaving }: EditProfileFormProps) {
  const { t } = useTranslation();

  // Form State
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
  const [scEligibilityStatus, setScEligibilityStatus] = useState(
    initialData.eligibility?.scEligibilityStatus ?? false
  );

  const [existingBusiness, setExistingBusiness] = useState(
    initialData.business?.existingBusiness ?? false
  );
  const [businessActivity, setBusinessActivity] = useState(initialData.business?.businessActivity || '');

  const handleSave = () => {
    // Validate
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
        coordinates: initialData.address?.coordinates, // Preserve existing coords
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

  const InputField = ({ label, value, onChangeText, keyboardType = 'default' }: any) => (
    <View style={styles.inputContainer}>
      <Text variant="caption" color={colors.textMuted} style={styles.inputLabel}>{label}</Text>
      <TextInput
        style={styles.input}
        value={value}
        onChangeText={onChangeText}
        keyboardType={keyboardType}
        placeholderTextColor={colors.textMuted}
      />
    </View>
  );

  return (
    <View style={styles.container}>
      {/* Personal Details */}
      <Text variant="subheading" style={styles.sectionTitle}>{t('profile.personalDetails', 'Personal Details')}</Text>
      <Card variant="glass">
        <InputField label={t('profile.fullName', 'Full Name')} value={fullName} onChangeText={setFullName} />
        <InputField label={t('profile.phoneNumber', 'Mobile Number')} value={phoneNumber} onChangeText={setPhoneNumber} keyboardType="phone-pad" />
        <InputField label={t('profile.email', 'Email Address')} value={email} onChangeText={setEmail} keyboardType="email-address" />
        <InputField label={t('profile.dateOfBirth', 'Date of Birth (YYYY-MM-DD)')} value={dateOfBirth} onChangeText={setDateOfBirth} />
      </Card>

      {/* Address Details */}
      <Text variant="subheading" style={styles.sectionTitle}>{t('profile.addressDetails', 'Address Details')}</Text>
      <Card variant="glass">
        <InputField label={t('profile.pinCode', 'PIN Code')} value={pinCode} onChangeText={setPinCode} keyboardType="number-pad" />
        <InputField label={t('profile.state', 'State')} value={stateName} onChangeText={setStateName} />
        <InputField label={t('profile.district', 'District')} value={district} onChangeText={setDistrict} />
        <InputField label={t('profile.city', 'City')} value={city} onChangeText={setCity} />
        <InputField label={t('profile.addressLine1', 'Address Line 1')} value={addressLine1} onChangeText={setAddressLine1} />
      </Card>

      {/* Education & Eligibility */}
      <Text variant="subheading" style={styles.sectionTitle}>{t('profile.educationAndEligibility', 'Education & Eligibility Details')}</Text>
      <Card variant="glass">
        <InputField label={t('profile.educationLevel', 'Education Level')} value={educationLevel} onChangeText={setEducationLevel} />
        <InputField label={t('profile.occupation', 'Occupation')} value={occupation} onChangeText={setOccupation} />
        <InputField label={t('profile.annualFamilyIncome', 'Annual Family Income (₹)')} value={annualFamilyIncome} onChangeText={setAnnualFamilyIncome} keyboardType="number-pad" />
        
        <View style={styles.switchContainer}>
          <Text variant="body" style={{ flex: 1 }}>{t('profile.scEligibility', 'SC Category Eligibility')}</Text>
          <Switch
            value={scEligibilityStatus}
            onValueChange={setScEligibilityStatus}
            trackColor={{ false: colors.borderStrong, true: colors.primary }}
          />
        </View>
      </Card>

      {/* Business Details */}
      <Text variant="subheading" style={styles.sectionTitle}>{t('profile.businessDetails', 'Business Details')}</Text>
      <Card variant="glass">
        <View style={styles.switchContainer}>
          <Text variant="body" style={{ flex: 1 }}>{t('profile.existingBusiness', 'Has Existing Business?')}</Text>
          <Switch
            value={existingBusiness}
            onValueChange={setExistingBusiness}
            trackColor={{ false: colors.borderStrong, true: colors.primary }}
          />
        </View>
        {existingBusiness && (
          <InputField label={t('profile.businessActivity', 'Business Activity')} value={businessActivity} onChangeText={setBusinessActivity} />
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
  switchContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingVertical: spacing.sm,
  },
  actions: {
    flexDirection: 'row',
    gap: spacing.md,
    marginTop: spacing.md,
  },
});
