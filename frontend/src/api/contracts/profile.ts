import { z } from 'zod';

/**
 * Persistent User Profile and Document Vault contracts.
 *
 * Distinct from the ephemeral ChatProfile used during the guided journey.
 * This profile persists across app restarts and loan applications.
 */

// ---------------------------------------------------------------------------
// Profile schemas
// ---------------------------------------------------------------------------

import { GeoPointSchema } from './common';

export const ProfileAddressSchema = z.object({
  state: z.string().optional(),
  district: z.string().optional(),
  city: z.string().optional(),
  pinCode: z.string().optional(),
  addressLine1: z.string().optional(),
  coordinates: GeoPointSchema.optional(),
});
export type ProfileAddress = z.infer<typeof ProfileAddressSchema>;

export const ProfileEligibilitySchema = z.object({
  scEligibilityStatus: z.boolean().nullable().optional(),
  annualFamilyIncome: z.number().nonnegative().nullable().optional(),
});
export type ProfileEligibility = z.infer<typeof ProfileEligibilitySchema>;

export const ProfileBusinessSchema = z.object({
  existingBusiness: z.boolean().nullable().optional(),
  businessActivity: z.string().optional(),
});
export type ProfileBusiness = z.infer<typeof ProfileBusinessSchema>;

export const ProfilePreferencesSchema = z.object({
  language: z.string().default('en'),
});

export const UserProfileSchema = z.object({
  id: z.string(),
  user_id: z.string(),
  fullName: z.string().nullable().optional(),
  phoneNumber: z.string().nullable().optional(),
  email: z.string().nullable().optional(),
  dateOfBirth: z.string().nullable().optional(),
  address: ProfileAddressSchema.default({}),
  eligibility: ProfileEligibilitySchema.default({}),
  business: ProfileBusinessSchema.default({}),
  preferences: ProfilePreferencesSchema.default({ language: 'en' }),
  createdAt: z.string(),
  updatedAt: z.string(),
});
export type UserProfile = z.infer<typeof UserProfileSchema>;

export const ProfileUpdateRequestSchema = z.object({
  fullName: z.string().optional(),
  phoneNumber: z.string().optional(),
  email: z.string().optional(),
  dateOfBirth: z.string().optional(),
  address: ProfileAddressSchema.optional(),
  eligibility: ProfileEligibilitySchema.optional(),
  business: ProfileBusinessSchema.optional(),
  preferences: ProfilePreferencesSchema.optional(),
});
export type ProfileUpdateRequest = z.infer<typeof ProfileUpdateRequestSchema>;

// ---------------------------------------------------------------------------
// Document Vault schemas
// ---------------------------------------------------------------------------

export const DOCUMENT_CATEGORIES = ['IDENTITY', 'ELIGIBILITY', 'FINANCIAL', 'BUSINESS', 'OTHER'] as const;
export type DocumentCategory = (typeof DOCUMENT_CATEGORIES)[number];

export const DOCUMENT_VERIFICATION_STATUSES = ['UPLOADED', 'VERIFIED', 'EXPIRED', 'REJECTED'] as const;
export type DocumentVerificationStatus = (typeof DOCUMENT_VERIFICATION_STATUSES)[number];

export const DocumentMetadataSchema = z.object({
  id: z.string(),
  documentType: z.string(),
  category: z.string(),
  originalFileName: z.string(),
  mimeType: z.string(),
  fileSizeBytes: z.number(),
  uploadedAt: z.string(),
  verificationStatus: z.string(),
  expiryDate: z.string().nullable().optional(),
});
export type DocumentMetadata = z.infer<typeof DocumentMetadataSchema>;

export const DocumentListResponseSchema = z.object({
  items: z.array(DocumentMetadataSchema),
});
export type DocumentListResponse = z.infer<typeof DocumentListResponseSchema>;

export const DocumentUploadRequestSchema = z.object({
  filename: z.string(),
  mimeType: z.string(),
  dataBase64: z.string(),
  documentType: z.string(),
  category: z.string(),
  expiryDate: z.string().optional(),
});
export type DocumentUploadRequest = z.infer<typeof DocumentUploadRequestSchema>;

// Predefined document types for UI dropdowns
export const DOCUMENT_TYPES_BY_CATEGORY: Record<DocumentCategory, { value: string; label: string }[]> = {
  IDENTITY: [
    { value: 'AADHAAR', label: 'Aadhaar Card' },
    { value: 'PAN', label: 'PAN Card' },
    { value: 'VOTER_ID', label: 'Voter ID' },
    { value: 'DRIVING_LICENCE', label: 'Driving Licence' },
  ],
  ELIGIBILITY: [
    { value: 'CASTE_CERTIFICATE', label: 'SC Caste Certificate' },
    { value: 'INCOME_CERTIFICATE', label: 'Income Certificate' },
    { value: 'DOMICILE_CERTIFICATE', label: 'Domicile Certificate' },
  ],
  FINANCIAL: [
    { value: 'BANK_STATEMENT', label: 'Bank Statement' },
    { value: 'INCOME_PROOF', label: 'Income Proof' },
    { value: 'SALARY_SLIP', label: 'Salary Slip' },
    { value: 'ITR', label: 'ITR / Tax Return' },
  ],
  BUSINESS: [
    { value: 'PROJECT_REPORT', label: 'Project Report' },
    { value: 'BUSINESS_REGISTRATION', label: 'Business Registration' },
    { value: 'GST_DOCUMENTS', label: 'GST Documents' },
    { value: 'EXISTING_BUSINESS_PROOF', label: 'Existing Business Proof' },
  ],
  OTHER: [
    { value: 'OTHER', label: 'Other Supporting Document' },
  ],
};
