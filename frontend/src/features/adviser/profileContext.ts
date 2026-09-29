import type { AssistantQueryRequest, UserProfile } from '@/api/contracts';
import { normalizeProfileLocation } from '@/profile/canonical';

type ProfileContext = NonNullable<AssistantQueryRequest['profileContext']>;

/**
 * Persistent profile facts the adviser may reuse. Conversation still owns the
 * current request; this must not trigger a profile write.
 */
export function buildAssistantProfileContext(
  profile: UserProfile | undefined | null,
): ProfileContext | undefined {
  if (!profile) return undefined;

  const ctx: ProfileContext = {};
  const income = profile.eligibility?.annualFamilyIncome;
  if (typeof income === 'number' && Number.isFinite(income)) {
    ctx.annualFamilyIncome = income;
  }
  const sc = profile.eligibility?.scEligibilityStatus;
  if (sc === true || sc === false) {
    ctx.scEligibilityStatus = sc;
  }
  const gender = profile.eligibility?.gender;
  if (gender === 'MALE' || gender === 'FEMALE' || gender === 'OTHER') {
    ctx.gender = gender;
  }
  const pin = profile.address?.pinCode;
  if (pin) ctx.pinCode = pin;
  const state = profile.address?.state;
  if (state) ctx.stateCode = state;

  const coords = normalizeProfileLocation(profile);
  if (coords) {
    ctx.latitude = coords.latitude;
    ctx.longitude = coords.longitude;
  }

  return Object.keys(ctx).length ? ctx : undefined;
}
