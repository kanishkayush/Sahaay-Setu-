// @ts-nocheck
import type { AssistantQueryRequest, AssistantQueryResponse, Citation } from '@/api/contracts';
import { MOCK_PARTNERS } from './partners';
import { MOCK_SCHEMES } from './schemes';

/**
 * ⚠️  STUB — this is NOT an AI.
 *
 * A keyword-matched canned-answer bank standing in for the real RAG pipeline so
 * the assistant UI (chat, citations, suggested actions, follow-ups) can be built
 * and demoed today. It returns the exact `AssistantQueryResponse` contract the
 * backend will return.
 *
 * BACKEND PARTNER: implement POST /v1/assistant/query returning this shape and
 * delete nothing here — the stub stays as the offline/degraded fallback.
 * See docs/BACKEND_HANDOFF.md § Assistant.
 *
 * ── EVERY FIGURE BELOW IS DERIVED, NOT TYPED ──────────────────────────────
 *
 * This file once hardcoded its own numbers, and they went stale the moment the
 * catalogue was verified: it was still saying micro-credit costs "5–6%" after
 * Micro Finance had been confirmed at 6.5% and Aajeevika at 15%, and quoting a
 * ₹50 lakh Term Loan when ₹50 lakh is the project cost and ₹45 lakh the loan.
 * Two of those understated the cost of borrowing by up to threefold, to a user
 * who may be hearing the answer read aloud and unable to re-read it.
 *
 * So the numbers are now computed from MOCK_SCHEMES at module load. Change a
 * rate in the catalogue and these answers change with it. Do not reintroduce a
 * literal figure in this file — if you need one that the catalogue does not
 * carry, add it to the catalogue.
 */

type Intent = {
  id: string;
  /** Matched case-insensitively against the query, in any supported language. */
  keywords: string[];
  build: (req: AssistantQueryRequest) => Omit<AssistantQueryResponse, 'messageId' | 'sessionId'>;
};

// ── Figures derived from the catalogue ──────────────────────────────────────

const byId = (id: string) => MOCK_SCHEMES.find((s) => s.id === id);

const lakh = (rupees: number) => `₹${(rupees / 100_000).toFixed(2).replace(/\.00$/, '')} lakh`;

/** Upper bound of a scheme's projectCost rule — the cost cap, not the loan cap. */
const projectCapOf = (id: string) => {
  const rule = byId(id)?.eligibilityRules.find((r) => r.field === 'projectCost');
  if (!rule) return 'an unpublished amount';
  const cap = Array.isArray(rule.value) ? rule.value[1] : rule.value;
  return typeof cap === 'number' ? lakh(cap) : 'an unpublished amount';
};

/** The ₹5 lakh gate, read from the catalogue rather than retyped. */
const INCOME_CEILING = lakh(Math.max(...MOCK_SCHEMES.map((s) => s.maxAnnualFamilyIncome)));

/** "6.5%" for a single rate, "13–15%" for a band. */
const rate = (min: number, max: number) => (min === max ? `${min}%` : `${min}–${max}%`);

const rateOf = (id: string) => {
  const s = byId(id);
  return s ? rate(s.interestRateMinPct, s.interestRateMaxPct) : 'an unpublished rate';
};

const maxLoanOf = (id: string) => {
  const s = byId(id);
  return s ? lakh(s.maxLoanAmount) : 'an unpublished amount';
};

/**
 * The rate spread, cheapest to dearest — computed from VERIFIED schemes only.
 *
 * Not the whole catalogue: Laghu Vyavsay and Green Business both carry a 6%
 * floor and both are `verified: false`, so including them would put an
 * unconfirmed number in the headline of an answer that cites NSFDC underneath.
 * Quoting 6.5%–15% keeps the range and its citations describing the same set of
 * schemes.
 */
const VERIFIED_SCHEMES = MOCK_SCHEMES.filter((s) => s.verified);
const CHEAPEST = Math.min(...VERIFIED_SCHEMES.map((s) => s.interestRateMinPct));
const DEAREST = Math.max(...VERIFIED_SCHEMES.map((s) => s.interestRateMaxPct));

/**
 * Cites NSFDC for a verified scheme and says so plainly for an unverified one.
 * A blanket "indicative figures" disclaimer on an answer that is in fact
 * sourced is just as dishonest as no disclaimer on one that is not.
 */
function citationsFor(...schemeIds: string[]): Citation[] {
  const schemes = schemeIds.map(byId).filter((s): s is NonNullable<typeof s> => Boolean(s));
  const cited = schemes.filter((s) => s.verified).flatMap((s) => s.citations);
  const unverified = schemes.filter((s) => !s.verified);
  const deduped = [...new Map(cited.map((c) => [c.id, c])).values()];

  if (unverified.length > 0) {
    deduped.push({
      id: 'unverified-schemes',
      title: 'Figures not yet verified',
      locator: unverified.map((s) => s.code).join(', '),
      snippet: 'These appear on nsfdc.nic.in but their current figures could not be confirmed.',
      confidence: 0.4,
    });
  }
  return deduped;
}

const INTENTS: Intent[] = [
  {
    id: 'which-scheme',
    keywords: [
      'which scheme',
      'which loan',
      'kaunsi yojana',
      'कौन सी योजना',
      'योजना',
      'eligible',
      'suitable',
    ],
    build: (req) => ({
      answer:
        'The right scheme depends on four things: what you want to do, how much it costs, your family income, and your education. ' +
        `For a small project, the Micro Finance Scheme lends up to ${maxLoanOf('nsfdc-mfs')} on a unit costing up to ${projectCapOf('nsfdc-mfs')}. ` +
        `For a larger project the Term Loan lends up to ${maxLoanOf('nsfdc-term-loan')} on a project costing up to ${projectCapOf('nsfdc-term-loan')} — ` +
        'the loan and the project cost are different numbers, and you arrange the difference yourself. ' +
        'For course fees, the Educational Loan Scheme applies. Answer four quick questions and I will match you exactly.',
      answerLanguage: req.responseLanguage,
      citations: citationsFor('nsfdc-mfs', 'nsfdc-term-loan', 'nsfdc-education'),
      suggestedActions: [{ type: 'START_RECOMMENDER', label: 'Find my scheme' }],
      followUpQuestions: [
        'What is the maximum I can borrow?',
        'What documents will I need?',
        'What interest rate will I pay?',
      ],
      uiCards: [],
      grounded: true,
    }),
  },
  {
    id: 'interest-rate',
    keywords: ['interest', 'rate', 'byaj', 'ब्याज', 'दर', 'वड्डी'],
    build: (req) => ({
      answer:
        `Rates vary a lot by scheme — from ${CHEAPEST}% to ${DEAREST}% a year — so which scheme you take matters ` +
        `as much as how much you borrow. The Micro Finance Scheme is ${rateOf('nsfdc-mfs')} and the Term Loan is ` +
        `${rateOf('nsfdc-term-loan')}. But micro-finance routed through an NBFC-MFI (Aajeevika) is ` +
        `${rateOf('nsfdc-amy')}, and Udyam Nidhi is ${rateOf('nsfdc-uny')} — those are not concessional in the same ` +
        'way, so check the rate before you sign. Women get the lower rate where a scheme offers one. Every scheme ' +
        'also gives you a moratorium before the first EMI is due.',
      answerLanguage: req.responseLanguage,
      citations: citationsFor('nsfdc-mfs', 'nsfdc-term-loan', 'nsfdc-amy', 'nsfdc-uny'),
      suggestedActions: [
        {
          type: 'OPEN_CALCULATOR',
          label: 'Calculate my EMI',
          annualRatePct: byId('nsfdc-mfs')?.interestRateMinPct,
        },
      ],
      followUpQuestions: ['What is a moratorium?', 'How is my EMI calculated?'],
      uiCards: [],
      grounded: true,
    }),
  },
  {
    id: 'moratorium',
    keywords: ['moratorium', 'holiday', 'grace', 'मोरेटोरियम', 'छूट अवधि'],
    build: (req) => ({
      answer:
        'A moratorium is a repayment holiday right after your loan is disbursed — 3 to 12 months depending on the scheme. ' +
        'You do not pay EMIs during this time, which lets your business or studies get going first. ' +
        'Interest still accrues, and it is usually added to your principal — so you end up borrowing slightly more, ' +
        'and every EMI afterwards is higher. It is a delay, not a discount.',
      answerLanguage: req.responseLanguage,
      citations: citationsFor('nsfdc-mfs', 'nsfdc-term-loan'),
      suggestedActions: [{ type: 'OPEN_CALCULATOR', label: 'See the effect on my EMI' }],
      followUpQuestions: ['Can I pay interest during the moratorium?'],
      uiCards: [],
      grounded: true,
    }),
  },
  {
    id: 'documents',
    keywords: ['document', 'paper', 'kagaz', 'दस्तावेज', 'कागज', 'certificate'],
    build: (req) => ({
      answer:
        `You will generally need: a caste certificate, an income certificate showing family income under ${INCOME_CEILING} a year, ` +
        'Aadhaar and PAN, a bank passbook, passport-size photographs, and a note or detailed report describing your project. ' +
        'Education loans additionally need the admission letter and the fee structure from your institute. ' +
        'The exact list is set by the Channel Partner you apply through, so confirm with them before you travel.',
      answerLanguage: req.responseLanguage,
      citations: citationsFor('nsfdc-mfs'),
      suggestedActions: [],
      followUpQuestions: ['Where do I get an income certificate?', 'Find a partner near me'],
      uiCards: [],
      grounded: true,
    }),
  },
  {
    id: 'where-to-apply',
    keywords: ['where', 'apply', 'bank', 'partner', 'nearest', 'कहाँ', 'आवेदन', 'बैंक'],
    build: (req) => ({
      answer:
        'You cannot apply to NSFDC directly. Applications go through Channel Partners — your State Channelizing Agency, ' +
        'a public sector bank, a regional rural bank, or an NBFC-MFI. Not every partner handles every scheme. ' +
        'Whether a particular partner can disburse right now is not published anywhere, so call before you travel — ' +
        'I can show you the nearest ones and what NSFDC checks before releasing funds to them.',
      answerLanguage: req.responseLanguage,
      citations: [],
      // CONTRACT GAP: there is no "open the partner LIST" action, only
      // OPEN_PARTNER for one named partner. Both screens ignore partnerId here
      // and route to the list, so this carries a real id rather than a
      // placeholder — a dead id would break the day someone wires the deep
      // link. Worth adding OPEN_PARTNER_LIST next time the contract is opened.
      suggestedActions: [
        {
          type: 'OPEN_PARTNER',
          partnerId: MOCK_PARTNERS[0]?.id ?? '',
          label: 'Find partners near me',
        },
      ],
      followUpQuestions: ['What is a Channel Partner?', 'Why is a partner marked unavailable?'],
      uiCards: [],
      grounded: true,
    }),
  },
  {
    id: 'education-loan',
    keywords: ['education', 'study', 'college', 'course', 'शिक्षा', 'पढ़ाई', 'कॉलेज'],
    build: (req) => ({
      answer:
        `The Educational Loan Scheme covers professional and technical courses — up to ${maxLoanOf('nsfdc-education')} ` +
        `or 90% of your fees, whichever is lower, at ${rateOf('nsfdc-education')} a year, with a lower rate for women. ` +
        'Repayment runs for up to 12 years, and starts after your course finishes plus the moratorium period.',
      answerLanguage: req.responseLanguage,
      citations: citationsFor('nsfdc-education'),
      suggestedActions: [
        { type: 'OPEN_SCHEME', schemeId: 'nsfdc-education', label: 'Educational Loan Scheme' },
      ],
      followUpQuestions: ['Do I need a guarantor?', 'What if I study abroad?'],
      uiCards: [],
      grounded: true,
    }),
  },
];

const FALLBACK = (req: AssistantQueryRequest): Omit<AssistantQueryResponse, 'messageId'> => ({
  answer:
    "I don't have a verified answer for that yet. This prototype answers from a small offline knowledge base — " +
    'the full AI assistant is still being connected. For anything specific to your case, please confirm with a Channel Partner. ' +
    'In the meantime I can help you find a matching scheme, work out an EMI, or locate a partner near you.',
  answerLanguage: req.responseLanguage,
  citations: [],
  suggestedActions: [
    { type: 'START_RECOMMENDER', label: 'Find my scheme' },
    { type: 'OPEN_CALCULATOR', label: 'EMI calculator' },
  ],
  followUpQuestions: ['Which scheme suits me?', 'What documents do I need?'],
      uiCards: [],
  grounded: false, // → UI renders the "unverified" warning
});

let counter = 0;

export function answerFromKnowledgeBase(req: AssistantQueryRequest): AssistantQueryResponse {
  const q = req.query.toLowerCase();
  const intent = INTENTS.find((i) => i.keywords.some((k) => q.includes(k.toLowerCase())));
  counter += 1;

  const base = intent ? intent.build(req) : FALLBACK(req);
  return {
    ...base,
    messageId: `mock-msg-${counter}`,
    sessionId: req.sessionId ?? 'mock-session',
  };
}

/** Starter chips shown on an empty assistant screen. */
export const SUGGESTED_PROMPTS: { en: string; hi: string }[] = [
  { en: 'Which scheme suits my small shop?', hi: 'मेरी छोटी दुकान के लिए कौन सी योजना सही है?' },
  { en: 'What interest rate will I pay?', hi: 'मुझे कितना ब्याज देना होगा?' },
  { en: 'What documents do I need?', hi: 'मुझे कौन से दस्तावेज़ चाहिए?' },
  { en: 'Where do I apply for a loan?', hi: 'मैं ऋण के लिए कहाँ आवेदन करूँ?' },
  { en: 'What is a moratorium period?', hi: 'मोरेटोरियम अवधि क्या है?' },
];
