# Translation glossary

The domain terms that must stay consistent across every locale. Translators:
settle these first, then the rest of the file follows. A screen that calls the
repayment holiday three different things is harder to use than one in English.

Status of each locale is recorded in its `_meta.reviewStatus`.

## Core financial terms

| English                   | हिन्दी               | मराठी                    | বাংলা                 | தமிழ்                       | తెలుగు                |
| ------------------------- | -------------------- | ------------------------ | --------------------- | --------------------------- | --------------------- |
| loan                      | ऋण                   | कर्ज                     | ঋণ                    | கடன்                        | రుణం                  |
| scheme                    | योजना                | योजना                    | প্রকল্প               | திட்டம்                     | పథకం                  |
| instalment (EMI)          | किस्त                | हप्ता                    | কিস্তি                | தவணை                        | వాయిదా                |
| interest                  | ब्याज                | व्याज                    | সুদ                   | வட்டி                       | వడ్డీ                 |
| interest rate             | ब्याज दर             | व्याज दर                 | সুদের হার             | வட்டி விகிதம்               | వడ్డీ రేటు            |
| principal                 | मूलधन                | मुद्दल                   | আসল                   | அசல்                        | అసలు                  |
| **moratorium**            | छूट अवधि             | सवलत कालावधी             | ছাড়ের সময়কাল        | சலுகைக் காலம்               | మారటోరియం             |
| tenure / repayment period | पुनर्भुगतान अवधि     | परतफेड कालावधी           | পরিশোধের মেয়াদ       | திருப்பிச் செலுத்தும் காலம் | తిరిగి చెల్లింపు కాలం |
| annual family income      | वार्षिक पारिवारिक आय | वार्षिक कौटुंबिक उत्पन्न | বার্ষিক পারিবারিক আয় | ஆண்டு குடும்ப வருமானம்      | వార్షిక కుటుంబ ఆదాయం  |
| project cost              | परियोजना लागत        | प्रकल्प खर्च             | প্রকল্পের খরচ         | திட்டச் செலவு               | ప్రాజెక్ట్ ఖర్చు      |
| concessional              | रियायती              | सवलतीचा                  | রেয়াতি               | சலுகை                       | రాయితీ                |
| Channel Partner           | चैनल साझेदार         | चॅनल भागीदार             | চ্যানেল পার্টনার      | சேனல் பங்குதாரர்            | ఛానల్ భాగస్వామి       |
| eligibility               | पात्रता              | पात्रता                  | যোগ্যতা               | தகுதி                       | అర్హత                 |
| documents                 | दस्तावेज़            | कागदपत्रे                | নথিপত্র               | ஆவணங்கள்                    | పత్రాలు               |
| lakh / crore              | लाख / करोड़          | लाख / कोटी               | লাখ / কোটি            | லட்சம் / கோடி               | లక్ష / కోటి           |

## Terms deliberately NOT translated

Transliterate or keep as-is — a literal translation means something else, or the
English is what people actually say:

- **NPA** — a defined regulatory term. Keep the acronym; expand once on first use.
- **EMI** — widely understood as-is across languages.
- **PIN code** — universally used in India.
- **SCA / PSB / RRB / NBFC-MFI** — institution categories, kept as acronyms.
- **NSFDC** — a proper noun.

## The three strings to get most right

Mistranslating these has real consequences for someone deciding whether to take
on debt:

1. `calculator.moratoriumHelp` — must convey that **interest still accrues**
   during the repayment holiday. Users routinely assume it does not.
2. `schemes.unverifiedNotice` — must convey that the figures are **not
   confirmed** and to check with a Channel Partner.
3. `partners.eligibility.highNpa` — must convey that an application here will
   likely be **delayed**, without implying the partner is fraudulent.

## Rules

- Interpolation placeholders (`{{count}}`, `{{rate}}`, `{{months}}`) are code.
  Translate around them, never through them.
- Endonyms in the `language` block are never translated.
- Keep sentences short. Long clauses wrap badly on a 360dp screen, and these
  scripts run longer than English.
