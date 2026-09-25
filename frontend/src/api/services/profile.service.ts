import { z } from 'zod';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { apiRequest } from '@/api/client';
import { USE_MOCK_API } from '@/api/config';
import { ENDPOINTS } from '@/api/endpoints';
import {
  UserProfileSchema,
  DocumentListResponseSchema,
  DocumentMetadataSchema,
  type UserProfile,
  type ProfileUpdateRequest,
  type DocumentUploadRequest,
  type DocumentMetadata,
  type DocumentListResponse,
} from '@/api/contracts';

// ---------------------------------------------------------------------------
// Stable device user ID
// ---------------------------------------------------------------------------

const USER_ID_STORAGE_KEY = 'saarthi.device-user-id';

let _cachedUserId: string | null = null;

function generateUUID(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === 'x' ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

/**
 * Returns a stable device-scoped user ID that persists across app restarts.
 * In production, replace with the authenticated user ID from auth middleware.
 */
export async function getDeviceUserId(): Promise<string> {
  if (_cachedUserId) return _cachedUserId;

  try {
    const stored = await AsyncStorage.getItem(USER_ID_STORAGE_KEY);
    if (stored) {
      _cachedUserId = stored;
      return stored;
    }
  } catch {
    // AsyncStorage unavailable (e.g. web without storage) — use in-memory ID
  }

  const newId = generateUUID();
  try {
    await AsyncStorage.setItem(USER_ID_STORAGE_KEY, newId);
  } catch {
    // Best effort
  }
  _cachedUserId = newId;
  return newId;
}

function userHeaders(_userId: string): Record<string, string> {
  // Bearer token is injected automatically by apiRequest (client.ts line 98-101).
  // X-User-Id is no longer used in production.
  return {};
}

// ---------------------------------------------------------------------------
// Profile services
// ---------------------------------------------------------------------------

export async function getProfile(): Promise<UserProfile> {
  if (USE_MOCK_API) {
    // Return an empty profile in mock mode
    return UserProfileSchema.parse({
      id: 'mock-profile-id',
      user_id: 'mock-user',
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    });
  }

  const userId = await getDeviceUserId();
  return apiRequest(ENDPOINTS.profile.get, UserProfileSchema, {
    method: 'GET',
    headers: userHeaders(userId),
  });
}

export async function updateProfile(request: ProfileUpdateRequest): Promise<UserProfile> {
  if (USE_MOCK_API) {
    return getProfile();
  }

  const userId = await getDeviceUserId();
  return apiRequest(ENDPOINTS.profile.update, UserProfileSchema, {
    method: 'PUT',
    body: request,
    headers: userHeaders(userId),
  });
}

// ---------------------------------------------------------------------------
// Document vault services
// ---------------------------------------------------------------------------

export async function listDocuments(): Promise<DocumentListResponse> {
  if (USE_MOCK_API) {
    return { items: [] };
  }

  const userId = await getDeviceUserId();
  return apiRequest(ENDPOINTS.profile.documents, DocumentListResponseSchema, {
    method: 'GET',
    headers: userHeaders(userId),
  });
}

export async function uploadDocument(formData: FormData): Promise<DocumentMetadata> {
  if (USE_MOCK_API) {
    return DocumentMetadataSchema.parse({
      id: generateUUID(),
      documentType: formData.get('documentType') as string,
      category: formData.get('category') as string,
      originalFileName: (formData.get('file') as any)?.name ?? 'mock_file',
      mimeType: (formData.get('file') as any)?.type ?? 'application/pdf',
      fileSizeBytes: 0,
      uploadedAt: new Date().toISOString(),
      verificationStatus: 'UPLOADED',
    });
  }

  const userId = await getDeviceUserId();
  return apiRequest(ENDPOINTS.profile.documents, DocumentMetadataSchema, {
    method: 'POST',
    body: formData,
    headers: userHeaders(userId),
  });
}

export async function deleteDocument(documentId: string): Promise<void> {
  if (USE_MOCK_API) return;

  const userId = await getDeviceUserId();
  // DELETE returns 204 No Content — use z.unknown() and discard
  await apiRequest(ENDPOINTS.profile.documentById(documentId), z.unknown(), {
    method: 'DELETE',
    headers: userHeaders(userId),
  });
}

export async function clearBackendProfile(): Promise<void> {
  if (USE_MOCK_API) return;

  const userId = await getDeviceUserId();
  await apiRequest('/v1/profile/clear', z.unknown(), {
    method: 'DELETE',
    headers: userHeaders(userId),
  });
}
