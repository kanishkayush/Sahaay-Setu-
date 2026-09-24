import type { Citation, PartnerType } from '@/api/contracts';

/**
 * NSFDC's published prudential norms, encoded per partner type.
 *
 * ── WHY THIS FILE EXISTS ──────────────────────────────────────────────────
 *
 * The problem statement asks us not to route applications to partners with
 * "high NPAs or overdues". A single "NPA below 10%" rule would be wrong for
 * every partner type NSFDC works with: an RRB may carry a net NPA up to 15%
 * and stay eligible, while an NBFC-MFI must stay below 0.5% — a thirtyfold
 * difference in the same network. Collapsing them into one threshold produces
 * a number that looks rigorous and is not.
 *
 * So the norms live here as data, keyed by partner type, each carrying the
 * source it came from and — this is the point — the exact field a data feed
 * would have to supply before the norm could actually be evaluated.
 *
 * ── WHAT THIS DOES NOT DO ─────────────────────────────────────────────────
 *
 * It does not compute partner health. NSFDC publishes the rules but not the
 * per-partner figures, so nothing here can be evaluated today. Every partner
 * is `status: 'UNKNOWN'`, and `requiredInputsFor()` names precisely what is
 * missing. That list is the ask for NSFDC, not a TODO for us.
 *
 * ── SOURCE PROVENANCE (checked 2026-09-07) ────────────────────────────────
 *
 * NSFDC restructured its site: `nsfdc.nic.in/scheme` serves 200, but every
 * `/en/*` path now returns 404, including the pages these norms come from.
 *
 * Every norm below was then read verbatim from a Wayback Machine capture of
 * the original NSFDC page — a permanent, resolvable URL with a capture date,
 * recorded as `retrievedVia: 'WEB_ARCHIVE_SNAPSHOT'`. That is a primary
 * document, not a paraphrase, so these are real citations.
 *
 * They are held at confidence 0.9 rather than 1: the captures are from 2024
 * and 2025 and NSFDC's live pages are gone, so a norm could have been revised
 * since without leaving a trace we can reach. Treat as accurate-as-of-capture.
 * ─────────────────────────────────────────────────────────────────────────
 */

const CHECKED = '2026-09-07';

type RetrievalMethod = 'LIVE_PAGE' | 'WEB_ARCHIVE_SNAPSHOT';

export type NormSource = Citation & {
  /**
   * How the text was obtained. An archive snapshot is the original NSFDC page
   * as captured on a stated date — a primary document at a permanent URL, but
   * one whose live counterpart no longer resolves.
   */
  retrievedVia: RetrievalMethod;
  /** ISO date of the archive capture the text was read from. */
  capturedOn?: string;
};

const WAYBACK = 'http://web.archive.org/web';

export const NORM_SOURCES = {
  allocation: {
    id: 'nsfdc-allocation-of-funds',
    title: 'NSFDC — Allocation of Funds (prudential norms)',
    locator: `nsfdc.nic.in/en/allocation-of-funds — 404 live on ${CHECKED}; read from the 2025-03-17 archive capture`,
    url: `${WAYBACK}/20250317020034/https://nsfdc.nic.in/en/allocation-of-funds`,
    retrievedVia: 'WEB_ARCHIVE_SNAPSHOT',
    capturedOn: '2025-03-17',
    confidence: 0.9,
  },
  standUpIndia: {
    id: 'nsfdc-stand-up-india',
    title: 'NSFDC — Stand-up India',
    locator: `nsfdc.nic.in/en/stand-up-india — 404 live on ${CHECKED}; read from the 2024-10-04 archive capture`,
    url: `${WAYBACK}/20241004121650/https://nsfdc.nic.in/en/stand-up-india`,
    retrievedVia: 'WEB_ARCHIVE_SNAPSHOT',
    capturedOn: '2024-10-04',
    confidence: 0.9,
  },
  nbfcMfi: {
    id: 'nsfdc-nbfc-mfi-criteria',
    title: 'NSFDC — Schemes to be implemented through NBFC-MFIs',
    locator: `nsfdc.nic.in/en/schemes-to-be-implemented-through-nbfc-mfis — 404 live on ${CHECKED}; read from the 2025-02-15 archive capture`,
    url: `${WAYBACK}/20250215112410/https://nsfdc.nic.in/en/schemes-to-be-implemented-through-nbfc-mfis`,
    retrievedVia: 'WEB_ARCHIVE_SNAPSHOT',
    capturedOn: '2025-02-15',
    confidence: 0.9,
  },
} as const satisfies Record<string, NormSource>;

export type NormSourceId = keyof typeof NORM_SOURCES;

/**
 * The data a feed would have to carry for a norm to be checkable. These are
 * the field names we would ask NSFDC for — none of them exist on
 * `PartnerEligibility` today except `npaPct`, `overdueAmount` and
 * `unutilisedLimit`, which are all optional and all currently absent.
 */
export type RequiredInput =
  | 'npaPct'
  | 'grossNpaPct'
  | 'netNpaHistory'
  | 'netProfitHistory'
  | 'overdueAmount'
  | 'unutilisedLimit'
  | 'guaranteeInPlace'
  | 'moaInForce'
  | 'utilisationCertificateFiled'
  | 'capacityAssessmentRating'
  | 'creditBureauMember'
  | 'borrowingDefaultHistory'
  | 'rbiRegistration';

export type EligibilityNorm = {
  id: string;
  /** i18n key under `partners.norms.rule.*`. Interpolation values in `values`. */
  labelKey: string;
  values?: Record<string, string | number>;
  /** What a data feed must supply before this norm can be evaluated. */
  requires: RequiredInput[];
  sourceId: NormSourceId;
};

/**
 * Applies to every partner type. These are conditions on the *release* of
 * funds, so they gate disbursement regardless of what kind of body the
 * partner is.
 */
export const COMMON_RELEASE_NORMS: EligibilityNorm[] = [
  {
    id: 'common-overdues',
    labelKey: 'partners.norms.rule.overdues',
    requires: ['overdueAmount'],
    sourceId: 'allocation',
  },
  {
    id: 'common-utilisation',
    labelKey: 'partners.norms.rule.utilisation',
    values: { pct: 80 },
    requires: ['unutilisedLimit'],
    sourceId: 'allocation',
  },
];

/** Conditions specific to what kind of institution the partner is. */
export const NORMS_BY_PARTNER_TYPE: Record<PartnerType, EligibilityNorm[]> = {
  SCA: [
    {
      id: 'sca-guarantee',
      labelKey: 'partners.norms.rule.guarantee',
      requires: ['guaranteeInPlace'],
      sourceId: 'allocation',
    },
  ],
  RRB: [
    {
      id: 'rrb-npa',
      labelKey: 'partners.norms.rule.rrbNpa',
      values: { pct: 15, years: 3, of: 6 },
      requires: ['netNpaHistory'],
      sourceId: 'allocation',
    },
    {
      id: 'rrb-profit',
      labelKey: 'partners.norms.rule.rrbProfit',
      values: { years: 3, of: 6 },
      requires: ['netProfitHistory'],
      sourceId: 'allocation',
    },
    {
      id: 'rrb-standup',
      labelKey: 'partners.norms.rule.rrbStandUp',
      values: { pct: 10 },
      requires: ['netNpaHistory'],
      sourceId: 'standUpIndia',
    },
  ],
  PSB: [
    {
      id: 'psb-moa',
      labelKey: 'partners.norms.rule.psbMoa',
      requires: ['moaInForce'],
      sourceId: 'allocation',
    },
    {
      id: 'psb-utilisation-certificate',
      labelKey: 'partners.norms.rule.psbUtilisationCertificate',
      requires: ['utilisationCertificateFiled'],
      sourceId: 'allocation',
    },
    {
      id: 'psb-no-overdue',
      labelKey: 'partners.norms.rule.psbNoOverdue',
      requires: ['overdueAmount'],
      sourceId: 'allocation',
    },
  ],
  NBFC_MFI: [
    {
      id: 'mfi-registration',
      labelKey: 'partners.norms.rule.mfiRegistration',
      requires: ['rbiRegistration'],
      sourceId: 'nbfcMfi',
    },
    {
      id: 'mfi-npa',
      labelKey: 'partners.norms.rule.mfiNpa',
      values: { gross: 2, net: 0.5 },
      requires: ['grossNpaPct', 'npaPct'],
      sourceId: 'nbfcMfi',
    },
    {
      id: 'mfi-profit',
      labelKey: 'partners.norms.rule.mfiProfit',
      values: { years: 3 },
      requires: ['netProfitHistory'],
      sourceId: 'nbfcMfi',
    },
    {
      id: 'mfi-rating',
      labelKey: 'partners.norms.rule.mfiRating',
      values: { rating: 'mfr5' },
      requires: ['capacityAssessmentRating'],
      sourceId: 'nbfcMfi',
    },
    {
      id: 'mfi-bureau',
      labelKey: 'partners.norms.rule.mfiBureau',
      requires: ['creditBureauMember'],
      sourceId: 'nbfcMfi',
    },
    {
      id: 'mfi-no-default',
      labelKey: 'partners.norms.rule.mfiNoDefault',
      values: { years: 3 },
      requires: ['borrowingDefaultHistory'],
      sourceId: 'nbfcMfi',
    },
  ],
  COOP_BANK: [],
  SFB: [],
  UNKNOWN: [],
};

/** Every norm that gates disbursement to a partner of this type. */
export function normsFor(type: PartnerType): EligibilityNorm[] {
  return [...NORMS_BY_PARTNER_TYPE[type], ...COMMON_RELEASE_NORMS];
}

/**
 * The distinct data fields NSFDC would have to publish before this partner's
 * status could be anything other than UNKNOWN. This is the R3 data ask,
 * derived rather than written down twice.
 */
export function requiredInputsFor(type: PartnerType): RequiredInput[] {
  const seen = new Set<RequiredInput>();
  for (const norm of normsFor(type)) {
    for (const input of norm.requires) seen.add(input);
  }
  return [...seen];
}

/** The source behind a norm, for rendering a citation next to it. */
export function sourceFor(norm: EligibilityNorm): NormSource {
  return NORM_SOURCES[norm.sourceId];
}
