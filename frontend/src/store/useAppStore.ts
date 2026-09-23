import AsyncStorage from '@react-native-async-storage/async-storage';
import { create } from 'zustand';
import { createJSONStorage, persist } from 'zustand/middleware';

import type { ApplicantProfile, LanguageCode } from '@/api/contracts';
import { changeLanguage } from '@/i18n';

/**
 * Persistent loan journey context. Carries the loan application state
 * across Guided Journey → Partner Selection → EMI Calculator navigation.
 * Repayment reminders are only activated once loanStatus = 'DISBURSED'.
 */
export type LoanJourneyContext = {
  schemeId?: string;
  schemeName?: string;
  requestedLoanAmount?: number;
  estimatedProjectCost?: number;
  interestRate?: number;
  tenureMonths?: number;
  selectedChannelPartnerId?: string;
  selectedChannelPartnerName?: string;
  loanStatus: 'DRAFT' | 'PARTNER_SELECTED' | 'APPLICATION_SUBMITTED' | 'APPROVED' | 'DISBURSED';
  approvalDate?: string;
  disbursementDate?: string;
  repaymentStartDate?: string;
};

const DEFAULT_LOAN_JOURNEY: LoanJourneyContext = {
  loanStatus: 'DRAFT',
};

export type AppState = {
  language: LanguageCode;
  hasCompletedOnboarding: boolean;
  authStatus: 'authenticated' | 'signed_out';
  profile: ApplicantProfile | null;
  savedSchemeIds: string[];
  /** Persistent loan journey context shared across all screens. */
  loanJourney: LoanJourneyContext;

  setLanguage: (code: LanguageCode) => Promise<void>;
  completeOnboarding: () => void;
  setAuthStatus: (status: 'authenticated' | 'signed_out') => void;
  setProfile: (profile: ApplicantProfile) => void;
  clearProfile: () => void;
  toggleSavedScheme: (schemeId: string) => void;
  isSchemeSaved: (schemeId: string) => boolean;
  setLoanJourney: (journey: LoanJourneyContext) => void;
  updateLoanJourney: (partial: Partial<LoanJourneyContext>) => void;
  clearLoanJourney: () => void;
  clearSession: () => void;
  reset: () => void;
};

const initialState = {
  language: 'en' as LanguageCode,
  hasCompletedOnboarding: false,
  authStatus: 'signed_out' as const,
  profile: null,
  savedSchemeIds: [] as string[],
  loanJourney: DEFAULT_LOAN_JOURNEY,
};

export const useAppStore = create<AppState>()(
  persist(
    (set, get) => ({
      ...initialState,

      setLanguage: async (code) => {
        await changeLanguage(code);
        set({ language: code });
      },

      completeOnboarding: () => set({ hasCompletedOnboarding: true }),

      setAuthStatus: (status) => set({ authStatus: status }),

      setProfile: (profile) => set({ profile }),

      clearProfile: () => set({ profile: null }),

      toggleSavedScheme: (schemeId) => {
        const current = get().savedSchemeIds;
        set({
          savedSchemeIds: current.includes(schemeId)
            ? current.filter((id) => id !== schemeId)
            : [...current, schemeId],
        });
      },

      isSchemeSaved: (schemeId) => get().savedSchemeIds.includes(schemeId),

      setLoanJourney: (journey) => set({ loanJourney: journey }),

      updateLoanJourney: (partial) =>
        set((state) => ({ loanJourney: { ...state.loanJourney, ...partial } })),

      clearLoanJourney: () => set({ loanJourney: DEFAULT_LOAN_JOURNEY }),

      clearSession: () => set({
        profile: null,
        savedSchemeIds: [],
        loanJourney: DEFAULT_LOAN_JOURNEY,
      }),

      reset: () => set(initialState),
    }),
    {
      name: 'sahaay.app-state',
      storage: createJSONStorage(() => AsyncStorage),
      partialize: (state) => ({
        language: state.language,
        hasCompletedOnboarding: state.hasCompletedOnboarding,
        profile: state.profile,
        savedSchemeIds: state.savedSchemeIds,
        loanJourney: state.loanJourney,
      }),
    },
  ),
);
