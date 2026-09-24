import { Alert, Pressable, ScrollView, StyleSheet, TextInput, View, ActivityIndicator, Platform } from 'react-native';
import { router } from 'expo-router';
import { useTranslation } from 'react-i18next';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import * as DocumentPicker from 'expo-document-picker';
import * as FileSystem from 'expo-file-system';
import { useState } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';

import { Banner, Button, Card, Chip, Screen, Text } from '@/components/ui';
import { SchemeCard } from '@/components/domain';
import { USE_MOCK_API } from '@/api/config';
import { useSchemes } from '@/hooks/useSchemes';
import { useLocation } from '@/hooks/useLocation';
import { SUPPORTED_LANGUAGES } from '@/i18n';
import { useAppStore } from '@/store/useAppStore';
import { colors, radius, spacing } from '@/theme';
import { formatCurrency } from '@/utils/format';
import {
  getProfile,
  updateProfile,
  listDocuments,
  uploadDocument,
  deleteDocument,
  clearBackendProfile,
} from '@/api/services';
import {
  DOCUMENT_CATEGORIES,
  DOCUMENT_TYPES_BY_CATEGORY,
  type DocumentCategory,
} from '@/api/contracts';

const APP_VERSION = '0.1.0';

const profileKeys = {
  profile: ['profile'] as const,
  documents: ['profile', 'documents'] as const,
};

export default function ProfileScreen() {
  const { t } = useTranslation();
  const language = useAppStore((s) => s.language);
  const setLanguage = useAppStore((s) => s.setLanguage);
  const profile = useAppStore((s) => s.profile);
  const authStatus = useAppStore((s) => s.authStatus);
  const setAuthStatus = useAppStore((s) => s.setAuthStatus);
  const clearProfile = useAppStore((s) => s.clearProfile);
  const savedIds = useAppStore((s) => s.savedSchemeIds);
  const queryClient = useQueryClient();

  const [activeTab, setActiveTab] = useState<'profile' | 'documents'>('profile');
  const [uploadingDocId, setUploadingDocId] = useState<string | null>(null);

  const { data: schemes } = useSchemes();
  const savedSchemes = (schemes?.items ?? []).filter((s) => savedIds.includes(s.id));

  // Persistent profile from backend
  const { data: persistentProfile, isLoading: profileLoading } = useQuery({
    queryKey: profileKeys.profile,
    queryFn: getProfile,
    enabled: !USE_MOCK_API,
  });

  const updateProfileMutation = useMutation({
    mutationFn: updateProfile,
    onSuccess: async (data) => {
      console.log('[LOCATION] profile update response=', JSON.stringify(data?.address));

      // Step 1: Invalidate and refetch the profile to verify backend persistence
      await queryClient.invalidateQueries({ queryKey: profileKeys.profile });
      const refetched = await queryClient.fetchQuery({
        queryKey: profileKeys.profile,
        queryFn: getProfile,
      });
      console.log('[LOCATION] persisted profile=', JSON.stringify(refetched?.address));

      // Step 2: Invalidate the entire partners query family
      await queryClient.invalidateQueries({ queryKey: ['partners'] });
      console.log('[LOCATION] partners query family invalidated');
    },
    onError: (err) => {
      console.error('[LOCATION] Profile update failed:', err);
      Alert.alert('Error', 'Failed to save profile changes.');
    },
  });

  // Documents
  const { data: documentsData, isLoading: docsLoading, refetch: refetchDocs } = useQuery({
    queryKey: profileKeys.documents,
    queryFn: listDocuments,
    enabled: !USE_MOCK_API,
  });
  const documents = documentsData?.items ?? [];

  const deleteDocumentMutation = useMutation({
    mutationFn: (docId: string) => {
      console.log('[DOCUMENT_DELETE] id=', docId);
      return deleteDocument(docId);
    },
    onSuccess: (_data, docId) => {
      console.log('[DOCUMENT_DELETE] success for id=', docId);
      void queryClient.invalidateQueries({ queryKey: profileKeys.documents });
    },
    onError: (err, docId) => {
      console.error('[DOCUMENT_DELETE] failed for id=', docId, err);
      Alert.alert('Error', 'Failed to delete document. Please try again.');
    },
  });

  const confirmClear = () => {
    const message = t('profile.clearWarning', 'This will reset your eligibility answers, loan journey, and saved schemes. Your uploaded documents will NOT be deleted.');
    
    if (Platform.OS === 'web') {
      if (window.confirm(`Clear saved answers?\n\n${message}`)) {
        void performDeepClear();
      }
      return;
    }

    Alert.alert(t('profile.clearTitle', 'Clear saved answers?'), message, [
      { text: t('common.cancel'), style: 'cancel' },
      { text: t('profile.clearConfirm', 'Clear answers'), style: 'destructive', onPress: performDeepClear },
    ]);
  };

  const performDeepClear = async () => {
    try {
      console.log('[CLEAR] Starting deep clear...');

      // 1. Clear backend profile eligibility data (but NOT documents)
      try {
        await updateProfile({
          eligibility: { scEligibilityStatus: null, annualFamilyIncome: null },
          business: { existingBusiness: null, businessActivity: undefined },
        });
        console.log('[CLEAR] backend profile eligibility cleared');
      } catch (e) {
        console.warn('[CLEAR] backend profile clear failed (non-fatal):', e);
      }

      // 2. Clear relevant React Query cache
      queryClient.removeQueries({ queryKey: ['partners'] });
      queryClient.removeQueries({ queryKey: ['schemes'] });
      queryClient.removeQueries({ queryKey: profileKeys.profile });
      console.log('[CLEAR] query cache cleared');
      
      // 3. Wipe Zustand persist store for eligibility answers, loan journey, and saved schemes
      useAppStore.getState().clearSession();
      console.log('[CLEAR] local state cleared');

      // 4. Remove session-specific AsyncStorage items ONLY
      await AsyncStorage.removeItem('sahaay.chat-state'); 
      await AsyncStorage.removeItem('conversation_id');
      console.log('[CLEAR] storage cleared');

      // 5. Refetch fresh profile
      void queryClient.invalidateQueries({ queryKey: profileKeys.profile });

      Alert.alert(t('profile.clearSuccess'), t('profile.clearSuccessMsg'));
    } catch (e) {
      console.error('[CLEAR] Failed to clear details:', e);
      Alert.alert(t('profile.clearError'), t('profile.clearErrorMsg'));
    }
  };

  const handleDocumentPick = async (category: DocumentCategory) => {
    console.log('[DOCUMENT] Upload button pressed for category:', category);
    try {
      const result = await DocumentPicker.getDocumentAsync({
        type: ['application/pdf', 'image/jpeg', 'image/png'],
        copyToCacheDirectory: true,
        multiple: false,
      });

      if (result.canceled || !result.assets?.[0]) {
        return;
      }

      const asset = result.assets[0];
      const tempId = Date.now().toString();
      setUploadingDocId(tempId);

      const defaultType = DOCUMENT_TYPES_BY_CATEGORY[category]?.[0]?.value ?? 'OTHER';

      const formData = new FormData();
      formData.append('documentType', defaultType);
      formData.append('category', category);
      
      if (asset.file) {
        formData.append('file', asset.file);
      } else {
        formData.append('file', {
          uri: asset.uri,
          name: asset.name,
          type: asset.mimeType ?? 'application/octet-stream',
        } as any);
      }

      await uploadDocument(formData);
      await refetchDocs();
    } catch (e) {
      Alert.alert('Upload failed', 'Could not upload the document. Please try again.');
    } finally {
      setUploadingDocId(null);
    }
  };

  const handleDeleteDocument = (documentId: string, fileName: string) => {
    Alert.alert('Delete Document', `Delete "${fileName}"?`, [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Delete',
        style: 'destructive',
        onPress: () => deleteDocumentMutation.mutate(documentId),
      },
    ]);
  };

  return (
    <Screen>
      {/* Header */}
      <View style={styles.header}>
        <Text variant="title">{t('profile.title')}</Text>
      </View>

      {/* Language */}
      <View style={styles.section}>
        <Text variant="subheading">{t('profile.language')}</Text>
        <View style={styles.langGrid}>
          {SUPPORTED_LANGUAGES.map((option) => {
            const selected = option.code === language;
            return (
              <Pressable
                key={option.code}
                accessibilityRole="radio"
                accessibilityState={{ selected }}
                accessibilityLabel={option.endonym}
                onPress={() => void setLanguage(option.code)}
                style={({ pressed }) => [
                  styles.langCard,
                  selected && styles.langSelected,
                  pressed && styles.pressed,
                ]}
              >
                <Text variant="bodyStrong" color={selected ? colors.surface : colors.text}>
                  {option.endonym}
                </Text>
              </Pressable>
            );
          })}
        </View>
      </View>

      {/* Primary Location */}
      {persistentProfile ? (
        <View style={styles.section}>
          <Text variant="subheading" style={{ marginBottom: spacing.xs }}>{t('profile.primaryLocation')}</Text>
          <LocationCard 
            profile={persistentProfile} 
            onUpdate={(address) => {
              console.log('[LOCATION] PROFILE_PAYLOAD:', JSON.stringify(address));
              updateProfileMutation.mutate({ address });
            }}
          />
        </View>
      ) : profileLoading ? (
        <ActivityIndicator color={colors.primary} />
      ) : null}

      {/* Tab navigation */}
      <View style={styles.tabRow}>
        <Pressable
          style={[styles.tab, activeTab === 'profile' && styles.tabActive]}
          onPress={() => setActiveTab('profile')}
        >
          <Text
            variant="bodyStrong"
            color={activeTab === 'profile' ? colors.primary : colors.textMuted}
          >
            {t('profile.myProfileTab')}
          </Text>
        </Pressable>
        <Pressable
          style={[styles.tab, activeTab === 'documents' && styles.tabActive]}
          onPress={() => setActiveTab('documents')}
        >
          <Text
            variant="bodyStrong"
            color={activeTab === 'documents' ? colors.primary : colors.textMuted}
          >
            {t('profile.myDocumentsTab')}
          </Text>
        </Pressable>
      </View>

      {/* Profile tab */}
      {activeTab === 'profile' && (
        <View style={styles.section}>
          {USE_MOCK_API ? (
            <Banner
              tone="info"
              message={t('profile.requireLiveBackendProfile')}
            />
          ) : profileLoading ? (
            <ActivityIndicator color={colors.primary} />
          ) : persistentProfile ? (
            <View>
              <Text variant="subheading" style={{ marginTop: spacing.md, marginBottom: spacing.xs }}>{t('profile.personalDetails')}</Text>
              <Card variant="glass">
                <ProfileField
                  label={t('profile.fullName')}
                  value={persistentProfile.fullName ?? ''}
                  onSave={(v) =>
                    updateProfileMutation.mutate({ fullName: v || undefined })
                  }
                />
                <ProfileField
                  label={t('profile.phoneNumber')}
                  value={persistentProfile.phoneNumber ?? ''}
                  onSave={(v) =>
                    updateProfileMutation.mutate({ phoneNumber: v || undefined })
                  }
                />
                <ProfileField
                  label={t('profile.educationLevel', 'Education Level')}
                  value={persistentProfile.educationLevel ?? ''}
                  onSave={(v) =>
                    updateProfileMutation.mutate({ educationLevel: v || undefined })
                  }
                />
                <ProfileField
                  label={t('profile.occupation', 'Occupation')}
                  value={persistentProfile.occupation ?? ''}
                  onSave={(v) =>
                    updateProfileMutation.mutate({ occupation: v || undefined })
                  }
                />
                <ProfileField
                  label={t('profile.annualFamilyIncome')}
                  value={
                    persistentProfile.eligibility?.annualFamilyIncome?.toString() ?? ''
                  }
                  onSave={(v) =>
                    updateProfileMutation.mutate({
                      eligibility: {
                        annualFamilyIncome: v ? parseInt(v, 10) : undefined,
                      },
                    })
                  }
                  keyboardType="number-pad"
                  last
                />
              </Card>
            </View>
          ) : null}

          {/* Recommender profile */}
          {profile ? (
            <View style={styles.section}>
              <Text variant="label" color={colors.textMuted}>
                {t('profile.lastRecommenderAnswers')}
              </Text>
              <Card variant="glass">
                <Row
                  label={t('recommender.projectTypeQuestion')}
                  value={t(`projectType.${profile.projectType}`)}
                />
                <Row
                  label={t('recommender.projectCostQuestion')}
                  value={formatCurrency(profile.estimatedProjectCost)}
                />
                <Row
                  label={t('recommender.incomeQuestion')}
                  value={formatCurrency(profile.annualFamilyIncome)}
                />
                <Row
                  label={t('recommender.educationQuestion')}
                  value={t(`education.${profile.educationStatus}`)}
                  last
                />
              </Card>
              <View style={styles.rowActions}>
                <Button
                  title={t('recommender.editAnswers')}
                  variant="outline"
                  size="sm"
                  fullWidth={false}
                  style={styles.rowAction}
                  onPress={() => router.push('/recommend')}
                />
                <Button
                  title={t('profile.clearAnswers', 'Clear Saved Answers')}
                  variant="danger"
                  size="sm"
                  fullWidth={false}
                  style={styles.rowAction}
                  onPress={confirmClear}
                />
              </View>
            </View>
          ) : (
            <View style={styles.section}>
              <Button
                title={t('profile.clearAnswers', 'Clear Saved Answers')}
                variant="danger"
                size="sm"
                onPress={confirmClear}
              />
            </View>
          )}

          {/* Saved schemes */}
          <View style={styles.section}>
            <Text variant="subheading">{t('profile.savedSchemes')}</Text>
            {savedSchemes.length === 0 ? (
              <Text variant="caption" color={colors.textMuted}>
                {t('profile.noSavedSchemes')}
              </Text>
            ) : (
              savedSchemes.map((scheme) => (
                <SchemeCard
                  key={scheme.id}
                  scheme={scheme}
                  language={language}
                  onPress={() => router.push(`/scheme/${scheme.id}`)}
                />
              ))
            )}
          </View>
        </View>
      )}

      {/* Documents tab */}
      {activeTab === 'documents' && (
        <View style={styles.section}>
          {USE_MOCK_API ? (
            <Banner
              tone="info"
              message="Document vault requires the live backend."
            />
          ) : docsLoading ? (
            <ActivityIndicator color={colors.primary} />
          ) : (
            <>
              {/* Upload buttons per category */}
              <View style={styles.section}>
                <Text variant="label" color={colors.textMuted}>
                  {t('profile.uploadDocument')}
                </Text>
                <View style={styles.chipRow}>
                  {DOCUMENT_CATEGORIES.map((cat) => (
                    <Chip
                      key={cat}
                      label={cat}
                      tone="primary"
                      onPress={() => void handleDocumentPick(cat)}
                    />
                  ))}
                </View>
                {uploadingDocId && (
                  <View style={styles.uploadProgress}>
                    <ActivityIndicator color={colors.primary} size="small" />
                    <Text variant="caption" color={colors.textMuted}>
                      {t('profile.uploading')}
                    </Text>
                  </View>
                )}
              </View>

              {/* Document list */}
              {documents.length === 0 ? (
                <Text variant="body" color={colors.textMuted} center>
                  {t('profile.noDocuments')}
                </Text>
              ) : (
                documents.map((doc) => (
                  <Card key={doc.id} variant="glass">
                    <View style={styles.docRow}>
                      <View style={styles.docInfo}>
                        <Text variant="bodyStrong">{doc.originalFileName}</Text>
                        <Text variant="caption" color={colors.textMuted}>
                          {doc.category} · {doc.documentType}
                        </Text>
                        <Text variant="caption" color={colors.textMuted}>
                          {(doc.fileSizeBytes / 1024).toFixed(1)} KB ·{' '}
                          {new Date(doc.uploadedAt).toLocaleDateString()}
                        </Text>
                        <Chip
                          label={doc.verificationStatus}
                          tone={doc.verificationStatus === 'VERIFIED' ? 'success' : 'neutral'}
                        />
                      </View>
                      <Button
                        title={t('profile.delete')}
                        variant="danger"
                        size="sm"
                        fullWidth={false}
                        onPress={() => handleDeleteDocument(doc.id, doc.originalFileName)}
                        loading={deleteDocumentMutation.isPending && deleteDocumentMutation.variables === doc.id}
                      />
                    </View>
                  </Card>
                ))
              )}
            </>
          )}
        </View>
      )}

      {/* Account Section */}
      <View style={styles.section}>
        <Text variant="subheading">{t('profile.account')}</Text>
        <Card variant="glass">
          {authStatus === 'authenticated' ? (
            <View style={styles.docRow}>
              <View style={styles.docInfo}>
                <Text variant="bodyStrong">{t('profile.signedIn')}</Text>
                <Text variant="caption" color={colors.textSecondary}>
                  {t('profile.signedInHint')}
                </Text>
              </View>
              <Button
                title={t('profile.signOut')}
                variant="outline"
                size="sm"
                fullWidth={false}
                onPress={() => {
                  setAuthStatus('signed_out');
                  router.replace('/login');
                }}
              />
            </View>
          ) : (
            <View style={styles.docRow}>
              <View style={styles.docInfo}>
                <Text variant="bodyStrong">{t('profile.notSignedIn')}</Text>
                <Text variant="caption" color={colors.textSecondary}>
                  {t('profile.notSignedInHint')}
                </Text>
              </View>
              <Button
                title={t('profile.logIn')}
                variant="primary"
                size="sm"
                fullWidth={false}
                onPress={() => router.push('/login')}
              />
            </View>
          )}
        </Card>
      </View>

      {/* About */}
      <View style={styles.section}>
        <Text variant="subheading">{t('profile.about')}</Text>
        <Card variant="glass">
          <Text variant="body" color={colors.textSecondary}>
            {t('profile.aboutBody')}
          </Text>
          <View style={styles.metaRow}>
            <Chip label={t('profile.version', { version: APP_VERSION })} tone="neutral" />
            <Chip
              label={USE_MOCK_API ? t('profile.dataSourceMock') : t('profile.dataSourceLive')}
              tone={USE_MOCK_API ? 'warning' : 'success'}
            />
          </View>
        </Card>
      </View>
    </Screen>
  );
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function ProfileField({
  label,
  value,
  onSave,
  keyboardType,
  last,
}: {
  label: string;
  value: string;
  onSave: (value: string) => void;
  keyboardType?: 'default' | 'number-pad' | 'email-address' | 'phone-pad';
  last?: boolean;
}) {
  const { t } = useTranslation();
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(value);

  const handleSave = () => {
    setEditing(false);
    if (draft !== value) onSave(draft);
  };

  return (
    <View style={[styles.row, !last && styles.rowBorder]}>
      <Text variant="caption" color={colors.textMuted} style={styles.rowLabel}>
        {label}
      </Text>
      {editing ? (
        <View style={styles.editRow}>
          <TextInput
            value={draft}
            onChangeText={setDraft}
            keyboardType={keyboardType ?? 'default'}
            style={styles.editInput}
            autoFocus
            onSubmitEditing={handleSave}
            returnKeyType="done"
            placeholderTextColor={colors.textMuted}
          />
          <Button title="Save" variant="primary" size="sm" fullWidth={false} onPress={handleSave} />
        </View>
      ) : (
        <Pressable onPress={() => { setDraft(value); setEditing(true); }}>
          <Text variant="bodyStrong" color={value ? colors.text : colors.textMuted}>
            {value || t('profile.tapToAdd', 'Tap to add')}
          </Text>
        </Pressable>
      )}
    </View>
  );
}

function LocationCard({
  profile,
  onUpdate,
}: {
  profile: any;
  onUpdate: (address: any) => void;
}) {
  const { t } = useTranslation();
  const { request, status } = useLocation();
  const [locationStatus, setLocationStatus] = useState<
    'idle' | 'detecting' | 'success' | 'error' | 'denied' | 'pin_failed'
  >('idle');

  const handleUseCurrentLocation = async () => {
    console.log('[LOCATION] button pressed — handleUseCurrentLocation');
    setLocationStatus('detecting');
    try {
      const result = await request();

      if (result && result.point) {
        console.log('[LOCATION] GPS obtained:', JSON.stringify(result.point));

        // Extract address fields from reverse geocode (may be null)
        const postalCode = result.addressData?.postalCode ?? null;
        const subregion = result.addressData?.subregion ?? null;
        const region = result.addressData?.region ?? null;

        // Validate PIN
        let pinCode = profile.address?.pinCode;
        if (postalCode && /^[0-9]{6}$/.test(postalCode.trim())) {
          pinCode = postalCode.trim();
          console.log('[LOCATION] valid PIN extracted:', pinCode);
        } else {
          console.warn('[LOCATION] PIN could not be determined. postalCode=', postalCode);
          setLocationStatus('pin_failed');
          // Still proceed — coordinates are valid even without PIN
        }

        const addressPayload = {
          ...profile.address,
          pinCode,
          district: subregion || profile.address?.district,
          state: region || profile.address?.state,
          coordinates: result.point,
        };

        console.log('[LOCATION] profile update payload=', JSON.stringify(addressPayload));
        onUpdate(addressPayload);
        if (locationStatus !== 'pin_failed') {
          setLocationStatus('success');
        }
      } else {
        // request() returned null — permission denied or GPS failure
        console.log('[LOCATION] request returned null. hook status=', status);
        if (status === 'denied') {
          setLocationStatus('denied');
        } else {
          setLocationStatus('error');
        }
      }
    } catch (e) {
      console.error('[LOCATION] handleUseCurrentLocation error:', e);
      setLocationStatus('error');
    }
  };

  // Derive button label and status message from locationStatus
  const buttonTitle = {
    idle: t('location.useCurrentLocation'),
    detecting: t('location.detectingLocation'),
    success: t('location.locationUpdated'),
    denied: t('location.useCurrentLocation'),
    error: t('location.useCurrentLocation'),
    pin_failed: t('location.locationUpdatedPinFailed'),
  }[locationStatus];

  const statusMessage = {
    idle: null,
    detecting: null,
    success: null,
    denied: t('location.permissionDenied'),
    error: t('location.unableToDetermine'),
    pin_failed: t('location.pinFailed'),
  }[locationStatus];

  const statusColor = locationStatus === 'denied' || locationStatus === 'error'
    ? colors.dangerText
    : colors.textMuted;

  return (
    <Card variant="glass">
      <ProfileField
        label={t('profile.pinCode')}
        value={profile.address?.pinCode ?? ''}
        onSave={(v) => {
          if (v && !/^[0-9]{6}$/.test(v)) {
            Alert.alert(t('profile.invalidPin'), t('profile.invalidPinMsg'));
            return;
          }
          onUpdate({ ...profile.address, pinCode: v || undefined });
        }}
        keyboardType="number-pad"
      />
      <ProfileField
        label={t('profile.district')}
        value={profile.address?.district ?? ''}
        onSave={(v) => onUpdate({ ...profile.address, district: v || undefined })}
      />
      <ProfileField
        label={t('profile.state')}
        value={profile.address?.state ?? ''}
        onSave={(v) => onUpdate({ ...profile.address, state: v || undefined })}
        last
      />
      <View style={{ marginTop: spacing.md }}>
        <Button
          title={buttonTitle}
          variant={locationStatus === 'success' || locationStatus === 'pin_failed' ? 'secondary' : 'outline'}
          size="sm"
          onPress={handleUseCurrentLocation}
          disabled={locationStatus === 'detecting'}
          loading={locationStatus === 'detecting'}
        />
        {statusMessage ? (
          <Text variant="caption" color={statusColor} style={{ marginTop: spacing.xs }}>
            {statusMessage}
          </Text>
        ) : null}
      </View>
    </Card>
  );
}

function Row({ label, value, last }: { label: string; value: string; last?: boolean }) {
  return (
    <View style={[styles.row, !last && styles.rowBorder]}>
      <Text variant="caption" color={colors.textMuted} style={styles.rowLabel}>
        {label}
      </Text>
      <Text variant="bodyStrong">{value}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  header: { marginTop: spacing.md },
  section: { gap: spacing.md },
  langGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.sm },
  langCard: {
    flexBasis: '31%',
    flexGrow: 1,
    alignItems: 'center',
    paddingVertical: spacing.md,
    paddingHorizontal: spacing.sm,
    backgroundColor: colors.glass,
    borderWidth: 1,
    borderColor: colors.glassBorder,
    borderRadius: radius.md,
    minHeight: 52,
    justifyContent: 'center',
  },
  langSelected: { borderColor: colors.primary, backgroundColor: colors.primary },
  pressed: { opacity: 0.85 },
  tabRow: {
    flexDirection: 'row',
    backgroundColor: colors.glass,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.glassBorder,
    padding: 4,
    gap: 4,
  },
  tab: {
    flex: 1,
    paddingVertical: spacing.md,
    alignItems: 'center',
    borderRadius: radius.sm + 2,
  },
  tabActive: { backgroundColor: colors.surface },
  row: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    gap: spacing.md,
    paddingVertical: spacing.md,
  },
  rowLabel: { flex: 1 },
  rowBorder: { borderBottomWidth: 1, borderBottomColor: colors.border },
  rowActions: { flexDirection: 'row', gap: spacing.sm },
  rowAction: { flex: 1 },
  metaRow: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.sm, marginTop: spacing.md },
  chipRow: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.sm },
  docRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    gap: spacing.sm,
  },
  docInfo: { flex: 1, gap: spacing.xs },
  uploadProgress: {
    flexDirection: 'row',
    gap: spacing.sm,
    alignItems: 'center',
    marginTop: spacing.sm,
  },
  editRow: { flex: 2, flexDirection: 'row', gap: spacing.sm, alignItems: 'center' },
  editInput: {
    flex: 1,
    borderWidth: 1.5,
    borderColor: colors.borderStrong,
    borderRadius: radius.md,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    color: colors.text,
    fontSize: 15,
    backgroundColor: colors.surface,
  },
});
