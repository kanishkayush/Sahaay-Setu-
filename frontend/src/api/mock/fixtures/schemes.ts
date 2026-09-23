// @ts-nocheck
import type { Scheme } from '@/api/contracts';

/**
 * NSFDC scheme catalogue.
 *
 * ── VERIFICATION STATUS (checked 2026-09-07) ──────────────────────────────
 *
 * Five schemes below carry `verified: true`. Their figures were read directly
 * from https://nsfdc.nic.in/scheme, NSFDC's own site, and each carries a
 * citation. The ₹5.00 lakh annual family income ceiling is confirmed twice —
 * by NSFDC and by the Ministry (socialjustice.gov.in/schemes/34) — effective
 * 7 January 2026.
 *
 * The rest carry `verified: false`. They appear on nsfdc.nic.in but their
 * figures could not be retrieved from an official page, and third-party
 * aggregators disagree with NSFDC and with each other (one lists Term Loan at
 * 9–10% where NSFDC says 8%, and Micro Finance at ₹60,000 where NSFDC says
 * ₹1.25 lakh). Those sites appear to quote figures from before the 01.10.2023
 * revision. Do not "verify" a scheme from an aggregator.
 *
 * TWO SCHEMES WERE REMOVED. Mahila Kisan Yojana and Shilpi Samridhi Yojana
 * were in the v0 seed data; one source reports both closed from 01.04.2020 for
 * lack of demand, while another still lists them as active. Unresolved
 * conflict, so they are not offered — recommending a discontinued scheme sends
 * someone to a branch for a product that does not exist.
 *
 * TO VERIFY THE REMAINDER: open the scheme's page on nsfdc.nic.in, confirm each
 * figure, add a Citation, and flip `verified` for that scheme alone.
 * ─────────────────────────────────────────────────────────────────────────
 */

const LAST_VERIFIED = '2026-09-07T00:00:00.000Z';
const INCOME_CEILING = 500_000; // ₹5.00 lakh, effective 07.01.2026

/** NSFDC's own scheme summary — the only source we treat as authoritative. */
const NSFDC_SCHEMES_PAGE = {
  id: 'nsfdc-scheme-page-2026-09',
  title: 'NSFDC — Schemes',
  locator: 'nsfdc.nic.in/scheme, retrieved 2026-09-07',
  url: 'https://nsfdc.nic.in/scheme',
  confidence: 1,
};

const MOSJE_ELIGIBILITY = {
  id: 'mosje-nsfdc-2026-09',
  title: 'Ministry of Social Justice and Empowerment — NSFDC',
  locator: 'socialjustice.gov.in/schemes/34, retrieved 2026-09-07 — income ceiling ₹5.00 lakh',
  url: 'https://socialjustice.gov.in/schemes/34',
  confidence: 1,
};

export const MOCK_SCHEMES: Scheme[] = [
  // ── VERIFIED against nsfdc.nic.in/scheme ─────────────────────────────────
  {
    id: 'nsfdc-mfs',
    code: 'NSFDC-MFS',
    name: {
      en: 'Micro Finance Scheme',
      hi: 'सूक्ष्म वित्त योजना',
      mr: 'सूक्ष्म वित्त योजना',
      bn: 'ক্ষুদ্র ঋণ প্রকল্প',
      ta: 'நுண் நிதி திட்டம்',
      te: 'సూక్ష్మ రుణ పథకం',
    },
    shortDescription: {
      en: 'Small loans for petty trade, vending and tiny self-employment units.',
      hi: 'छोटे व्यापार, फेरी और अति लघु स्वरोजगार इकाइयों के लिए छोटे ऋण।',
    },
    officialCategory: 'ECONOMIC_DEVELOPMENT',
    recommendationCategory: 'RECOMMENDED',
    channelPartnerRequired: false,
    // Unit cost up to ₹1.40 lakh; NSFDC funds 90%, max ₹1.25 lakh per unit.
    minLoanAmount: 10_000,
    maxLoanAmount: 125_000,
    fundingSharePct: 0.9,
    interestRateMinPct: 6.5,
    interestRateMaxPct: 6.5,
    maxTenureMonths: 36,
    moratoriumMinMonths: 3,
    moratoriumMaxMonths: 3,
    maxAnnualFamilyIncome: INCOME_CEILING,
    eligibleGender: 'ANY',
    eligibilityRules: [
      {
        field: 'annualFamilyIncome',
        operator: 'lte',
        value: INCOME_CEILING,
        label: {
          en: 'Annual family income up to ₹5.00 lakh',
          hi: 'वार्षिक पारिवारिक आय ₹5.00 लाख तक',
        },
      },
      {
        field: 'projectCost',
        operator: 'lte',
        value: 140_000,
        label: { en: 'Unit cost up to ₹1.40 lakh', hi: 'इकाई लागत ₹1.40 लाख तक' },
      },
    ],
    documentsRequired: [
      { en: 'Caste certificate', hi: 'जाति प्रमाण पत्र' },
      { en: 'Income certificate', hi: 'आय प्रमाण पत्र' },
      { en: 'Aadhaar and PAN', hi: 'आधार और पैन' },
      { en: 'Project / activity note', hi: 'परियोजना विवरण' },
    ],
    channelPartnerTypes: ['SCA', 'NBFC_MFI', 'RRB'],
    citations: [NSFDC_SCHEMES_PAGE, MOSJE_ELIGIBILITY],
    verified: true,
    lastUpdatedAt: LAST_VERIFIED,
  },
  {
    id: 'nsfdc-term-loan',
    code: 'NSFDC-TL',
    name: {
      en: 'Term Loan',
      hi: 'सावधि ऋण',
      mr: 'मुदत कर्ज',
      bn: 'মেয়াদি ঋণ',
      ta: 'கால கடன்',
      te: 'కాల రుణం',
    },
    shortDescription: {
      en: 'For larger self-employment projects — manufacturing, transport, service ventures.',
      hi: 'बड़ी स्वरोजगार परियोजनाओं के लिए — विनिर्माण, परिवहन और सेवा उद्यम।',
    },
    officialCategory: 'ECONOMIC_DEVELOPMENT',
    recommendationCategory: 'RECOMMENDED',
    channelPartnerRequired: false,
    // Project cost above ₹1.25 lakh up to ₹50 lakh; NSFDC funds 90%, max ₹45 lakh.
    minLoanAmount: 125_001,
    maxLoanAmount: 4_500_000,
    fundingSharePct: 0.9,
    interestRateMinPct: 8,
    interestRateMaxPct: 8,
    maxTenureMonths: 84,
    // 6 months, except plantation and construction where it is 12.
    moratoriumMinMonths: 6,
    moratoriumMaxMonths: 12,
    maxAnnualFamilyIncome: INCOME_CEILING,
    eligibleGender: 'ANY',
    eligibilityRules: [
      {
        field: 'annualFamilyIncome',
        operator: 'lte',
        value: INCOME_CEILING,
        label: {
          en: 'Annual family income up to ₹5.00 lakh',
          hi: 'वार्षिक पारिवारिक आय ₹5.00 लाख तक',
        },
      },
      {
        field: 'projectCost',
        operator: 'between',
        value: [140_000, 5_000_000],
        label: {
          en: 'Project cost above ₹1.25 lakh and up to ₹50 lakh',
          hi: 'परियोजना लागत ₹1.25 लाख से अधिक और ₹50 लाख तक',
        },
      },
    ],
    documentsRequired: [
      { en: 'Caste certificate', hi: 'जाति प्रमाण पत्र' },
      { en: 'Income certificate', hi: 'आय प्रमाण पत्र' },
      { en: 'Detailed project report', hi: 'विस्तृत परियोजना रिपोर्ट' },
      { en: 'Quotations for machinery / vehicle', hi: 'मशीनरी / वाहन के कोटेशन' },
    ],
    channelPartnerTypes: ['SCA', 'PSB', 'RRB'],
    citations: [NSFDC_SCHEMES_PAGE, MOSJE_ELIGIBILITY],
    verified: true,
    lastUpdatedAt: LAST_VERIFIED,
  },
  {
    id: 'nsfdc-education',
    code: 'NSFDC-ELS',
    name: {
      en: 'Educational Loan Scheme',
      hi: 'शैक्षिक ऋण योजना',
      mr: 'शैक्षणिक कर्ज योजना',
      bn: 'শিক্ষা ঋণ প্রকল্প',
      ta: 'கல்விக் கடன் திட்டம்',
      te: 'విద్యా రుణ పథకం',
    },
    shortDescription: {
      en: 'Professional and technical courses, in India or abroad. Repayment starts after the course.',
      hi: 'भारत या विदेश में व्यावसायिक एवं तकनीकी पाठ्यक्रम। पुनर्भुगतान पाठ्यक्रम के बाद।',
    },
    officialCategory: 'EDUCATION',
    recommendationCategory: 'RECOMMENDED',
    channelPartnerRequired: false,
    // ₹40 lakh or 90% of course fee, whichever is less.
    minLoanAmount: 50_000,
    maxLoanAmount: 4_000_000,
    fundingSharePct: 0.9,
    interestRateMinPct: 6.5,
    interestRateMaxPct: 6.5,
    // Up to 12 years. Moratorium is course duration plus 1 year (or 6 months);
    // the app models only the post-course window.
    maxTenureMonths: 144,
    moratoriumMinMonths: 6,
    moratoriumMaxMonths: 12,
    maxAnnualFamilyIncome: INCOME_CEILING,
    eligibleGender: 'ANY',
    eligibilityRules: [
      {
        field: 'educationStatus',
        operator: 'in',
        value: ['HIGHER_SECONDARY', 'GRADUATE', 'POSTGRADUATE', 'VOCATIONAL'],
        label: {
          en: 'Admitted to a recognised professional or technical course',
          hi: 'मान्यता प्राप्त व्यावसायिक या तकनीकी पाठ्यक्रम में प्रवेश',
        },
      },
    ],
    documentsRequired: [
      { en: 'Admission letter', hi: 'प्रवेश पत्र' },
      { en: 'Fee structure from institute', hi: 'संस्थान की शुल्क संरचना' },
      { en: 'Caste and income certificates', hi: 'जाति और आय प्रमाण पत्र' },
    ],
    channelPartnerTypes: ['SCA', 'PSB'],
    citations: [NSFDC_SCHEMES_PAGE, MOSJE_ELIGIBILITY],
    verified: true,
    lastUpdatedAt: LAST_VERIFIED,
  },
  {
    id: 'nsfdc-amy',
    code: 'NSFDC-AMY',
    name: {
      en: 'Aajeevika Micro-Finance Yojana',
      hi: 'आजीविका सूक्ष्म वित्त योजना',
      mr: 'आजीविका सूक्ष्म वित्त योजना',
      bn: 'আজীবিকা ক্ষুদ্র ঋণ যোজনা',
      ta: 'ஆஜீவிகா நுண் நிதி யோஜனா',
      te: 'ఆజీవిక సూక్ష్మ రుణ యోజన',
    },
    shortDescription: {
      en: 'Micro-finance routed through NBFC-MFIs. Faster to access, but a much higher rate.',
      hi: 'एनबीएफसी-एमएफआई के माध्यम से सूक्ष्म वित्त। जल्दी उपलब्ध, पर ब्याज दर काफी अधिक।',
    },
    officialCategory: 'ECONOMIC_DEVELOPMENT',
    recommendationCategory: 'RECOMMENDED',
    channelPartnerRequired: false,
    minLoanAmount: 10_000,
    maxLoanAmount: 125_000,
    fundingSharePct: 0.9,
    interestRateMinPct: 15,
    interestRateMaxPct: 15,
    maxTenureMonths: 36,
    moratoriumMinMonths: 3,
    moratoriumMaxMonths: 3,
    maxAnnualFamilyIncome: INCOME_CEILING,
    eligibleGender: 'ANY',
    eligibilityRules: [
      {
        field: 'projectCost',
        operator: 'lte',
        value: 140_000,
        label: { en: 'Unit cost up to ₹1.40 lakh', hi: 'इकाई लागत ₹1.40 लाख तक' },
      },
    ],
    documentsRequired: [
      { en: 'Caste certificate', hi: 'जाति प्रमाण पत्र' },
      { en: 'Income certificate', hi: 'आय प्रमाण पत्र' },
    ],
    channelPartnerTypes: ['NBFC_MFI'],
    citations: [NSFDC_SCHEMES_PAGE],
    verified: true,
    lastUpdatedAt: LAST_VERIFIED,
  },
  {
    id: 'nsfdc-uny',
    code: 'NSFDC-UNY',
    name: {
      en: 'Udyam Nidhi Yojana',
      hi: 'उद्यम निधि योजना',
      mr: 'उद्यम निधी योजना',
      bn: 'উদ্যম নিধি যোজনা',
      ta: 'உத்யம் நிதி யோஜனா',
      te: 'ఉద్యమ్ నిధి యోజన',
    },
    shortDescription: {
      en: 'Mid-sized business loans through cooperative banks and small finance banks.',
      hi: 'सहकारी बैंकों और लघु वित्त बैंकों के माध्यम से मध्यम आकार के व्यवसाय ऋण।',
    },
    officialCategory: 'ECONOMIC_DEVELOPMENT',
    recommendationCategory: 'RECOMMENDED',
    channelPartnerRequired: false,
    minLoanAmount: 50_000,
    maxLoanAmount: 450_000,
    fundingSharePct: 0.9,
    // 13% via cooperative banks, 15% via small finance banks.
    interestRateMinPct: 13,
    interestRateMaxPct: 15,
    maxTenureMonths: 60,
    moratoriumMinMonths: 3,
    moratoriumMaxMonths: 3,
    maxAnnualFamilyIncome: INCOME_CEILING,
    eligibleGender: 'ANY',
    eligibilityRules: [
      {
        field: 'projectCost',
        operator: 'lte',
        value: 500_000,
        label: { en: 'Project cost up to ₹5.00 lakh', hi: 'परियोजना लागत ₹5.00 लाख तक' },
      },
    ],
    documentsRequired: [
      { en: 'Caste and income certificates', hi: 'जाति और आय प्रमाण पत्र' },
      { en: 'Business plan', hi: 'व्यवसाय योजना' },
    ],
    channelPartnerTypes: ['SCA', 'PSB'],
    citations: [NSFDC_SCHEMES_PAGE],
    verified: true,
    lastUpdatedAt: LAST_VERIFIED,
  },

  // ── LISTED BY NSFDC, FIGURES NOT YET CONFIRMED FROM AN OFFICIAL PAGE ──────
  {
    id: 'nsfdc-msy',
    code: 'NSFDC-MSY',
    name: {
      en: 'Mahila Samriddhi Yojana',
      hi: 'महिला समृद्धि योजना',
      mr: 'महिला समृद्धी योजना',
      bn: 'মহিলা সমৃদ্ধি যোজনা',
      ta: 'மகிளா சம்ரித்தி யோஜனா',
      te: 'మహిళా సమృద్ధి యోజన',
    },
    shortDescription: {
      en: 'Micro-credit for SC women entrepreneurs. Figures below are not yet confirmed.',
      hi: 'अनुसूचित जाति महिला उद्यमियों के लिए सूक्ष्म ऋण। नीचे दिए आंकड़े अभी असत्यापित हैं।',
    },
    officialCategory: 'ECONOMIC_DEVELOPMENT',
    recommendationCategory: 'RECOMMENDED',
    channelPartnerRequired: false,
    minLoanAmount: 10_000,
    maxLoanAmount: 140_000,
    fundingSharePct: 0.9,
    interestRateMinPct: 6.5,
    interestRateMaxPct: 8,
    maxTenureMonths: 48,
    moratoriumMinMonths: 3,
    moratoriumMaxMonths: 6,
    maxAnnualFamilyIncome: INCOME_CEILING,
    eligibleGender: 'FEMALE',
    eligibilityRules: [
      {
        field: 'gender',
        operator: 'eq',
        value: 'FEMALE',
        label: { en: 'Women beneficiaries only', hi: 'केवल महिला लाभार्थी' },
      },
    ],
    documentsRequired: [
      { en: 'Caste certificate', hi: 'जाति प्रमाण पत्र' },
      { en: 'Income certificate', hi: 'आय प्रमाण पत्र' },
    ],
    channelPartnerTypes: ['SCA', 'NBFC_MFI'],
    citations: [],
    verified: false,
    lastUpdatedAt: LAST_VERIFIED,
  },
  {
    id: 'nsfdc-lvy',
    code: 'NSFDC-LVY',
    name: {
      en: 'Laghu Vyavsay Yojana',
      hi: 'लघु व्यवसाय योजना',
      mr: 'लघु व्यवसाय योजना',
      bn: 'লঘু ব্যবসায় যোজনা',
      ta: 'லகு வியாபார யோஜனா',
      te: 'లఘు వ్యాపార యోజన',
    },
    shortDescription: {
      en: 'Small business loans — shops, service outlets, light trading. Figures not yet confirmed.',
      hi: 'लघु व्यवसाय ऋण — दुकानें, सेवा केंद्र, हल्का व्यापार। आंकड़े अभी असत्यापित।',
    },
    officialCategory: 'ECONOMIC_DEVELOPMENT',
    recommendationCategory: 'RECOMMENDED',
    channelPartnerRequired: false,
    minLoanAmount: 100_000,
    maxLoanAmount: 500_000,
    fundingSharePct: 0.9,
    interestRateMinPct: 6,
    interestRateMaxPct: 8,
    maxTenureMonths: 72,
    moratoriumMinMonths: 3,
    moratoriumMaxMonths: 6,
    maxAnnualFamilyIncome: INCOME_CEILING,
    eligibleGender: 'ANY',
    eligibilityRules: [
      {
        field: 'projectCost',
        operator: 'lte',
        value: 500_000,
        label: { en: 'Project cost up to ₹5.00 lakh', hi: 'परियोजना लागत ₹5.00 लाख तक' },
      },
    ],
    documentsRequired: [
      { en: 'Shop / trade licence if applicable', hi: 'दुकान / व्यापार लाइसेंस (यदि लागू)' },
      { en: 'Caste and income certificates', hi: 'जाति और आय प्रमाण पत्र' },
    ],
    channelPartnerTypes: ['SCA', 'PSB', 'RRB'],
    citations: [],
    verified: false,
    lastUpdatedAt: LAST_VERIFIED,
  },
  {
    id: 'nsfdc-gbs',
    code: 'NSFDC-GBS',
    name: {
      en: 'Green Business Scheme',
      hi: 'हरित व्यवसाय योजना',
      mr: 'हरित व्यवसाय योजना',
      bn: 'সবুজ ব্যবসা প্রকল্প',
      ta: 'பசுமை வணிகத் திட்டம்',
      te: 'హరిత వ్యాపార పథకం',
    },
    shortDescription: {
      en: 'E-rickshaws, solar units and other clean-energy livelihood assets. Figures not yet confirmed.',
      hi: 'ई-रिक्शा, सौर इकाइयाँ और अन्य स्वच्छ ऊर्जा आजीविका संपत्तियाँ। आंकड़े अभी असत्यापित।',
    },
    officialCategory: 'ECONOMIC_DEVELOPMENT',
    recommendationCategory: 'RECOMMENDED',
    channelPartnerRequired: false,
    minLoanAmount: 50_000,
    maxLoanAmount: 300_000,
    fundingSharePct: 0.9,
    interestRateMinPct: 6,
    interestRateMaxPct: 8,
    maxTenureMonths: 60,
    moratoriumMinMonths: 3,
    moratoriumMaxMonths: 6,
    maxAnnualFamilyIncome: INCOME_CEILING,
    eligibleGender: 'ANY',
    eligibilityRules: [
      {
        field: 'projectType',
        operator: 'in',
        value: ['TRANSPORT_VEHICLE', 'SERVICES'],
        label: {
          en: 'Clean-energy transport or service asset',
          hi: 'स्वच्छ ऊर्जा परिवहन या सेवा संपत्ति',
        },
      },
    ],
    documentsRequired: [
      { en: 'Vehicle quotation', hi: 'वाहन कोटेशन' },
      { en: 'Driving licence (for vehicles)', hi: 'ड्राइविंग लाइसेंस (वाहन हेतु)' },
    ],
    channelPartnerTypes: ['SCA', 'NBFC_MFI', 'RRB'],
    citations: [],
    verified: false,
    lastUpdatedAt: LAST_VERIFIED,
  },
];

export const SCHEME_DATA_DISCLAIMER = {
  en: 'Five schemes here were verified against nsfdc.nic.in on 7 September 2026. The rest are marked unverified and their figures may be wrong. Always confirm with a Channel Partner before applying.',
  hi: 'यहाँ पाँच योजनाएँ 7 सितंबर 2026 को nsfdc.nic.in से सत्यापित हैं। शेष असत्यापित हैं और उनके आंकड़े गलत हो सकते हैं। आवेदन से पहले चैनल साझेदार से पुष्टि अवश्य करें।',
  mr: 'येथील पाच योजना 7 सप्टेंबर 2026 रोजी nsfdc.nic.in वरून पडताळल्या आहेत. उर्वरित असत्यापित आहेत. अर्जापूर्वी चॅनल भागीदाराकडून खात्री करा.',
  bn: 'এখানে পাঁচটি প্রকল্প ৭ সেপ্টেম্বর ২০২৬-এ nsfdc.nic.in থেকে যাচাই করা হয়েছে। বাকিগুলি অযাচাইকৃত। আবেদনের আগে চ্যানেল পার্টনারের কাছে নিশ্চিত করুন।',
  ta: 'இங்குள்ள ஐந்து திட்டங்கள் 7 செப்டம்பர் 2026 அன்று nsfdc.nic.in இல் சரிபார்க்கப்பட்டன. மற்றவை சரிபார்க்கப்படவில்லை. விண்ணப்பிக்கும் முன் சேனல் பங்குதாரரிடம் உறுதிப்படுத்துங்கள்.',
  te: 'ఇక్కడి ఐదు పథకాలు 7 సెప్టెంబర్ 2026న nsfdc.nic.in నుండి ధృవీకరించబడ్డాయి. మిగిలినవి ధృవీకరించబడలేదు. దరఖాస్తుకు ముందు ఛానల్ భాగస్వామితో నిర్ధారించుకోండి.',
};
