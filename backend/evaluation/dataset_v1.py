"""Versioned, corpus-grounded multilingual adviser evaluation dataset."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EvalCase:
    id: str
    query: str
    language: str
    domain: str | None
    assistance_type: str | None
    expected_scheme_ids: tuple[str, ...]
    group: str
    variant: str = "other"


EDUCATION_ID = "nsfdc-education"
TERM_ID = "nsfdc-term-loan"
BUSINESS_IDS = (
    TERM_ID,
    "nsfdc-mfs",
    "nsfdc-amy",
    "nsfdc-uny",
)

_EDU_EN = [
    "I need a loan for my studies", "How can I finance college?", "I need an education loan",
    "Loan for BTech fees", "I need money for engineering", "Can NSFDC fund my MBBS course?",
    "College fee loan", "Finance for a professional course", "Student loan for higher education",
    "I want to study nursing with a loan", "Loan for an MBA course", "Help pay my diploma fees",
    "I need credit for technical education", "Funding for university tuition", "Study loan for BCA",
    "Education finance for pharmacy", "I need four lakh for college", "Loan to complete my degree",
    "Can I borrow for an approved course?", "Financial help for postgraduate studies",
]
_EDU_HI = [
    "मुझे पढ़ाई के लिए लोन चाहिए", "कॉलेज की फीस के लिए ऋण चाहिए", "बीटेक के लिए चार लाख चाहिए",
    "उच्च शिक्षा के लिए लोन बताइए", "इंजीनियरिंग की पढ़ाई के लिए पैसा चाहिए", "एमबीबीएस के लिए शिक्षा ऋण चाहिए",
    "नर्सिंग कोर्स की फीस भरनी है", "तकनीकी कोर्स के लिए ऋण", "डिप्लोमा पढ़ने के लिए लोन चाहिए",
    "विश्वविद्यालय की फीस के लिए सहायता", "फार्मेसी कोर्स के लिए लोन", "एमबीए की पढ़ाई के लिए पैसा",
    "मुझे छात्र शिक्षा ऋण चाहिए", "पेशेवर कोर्स के लिए वित्त चाहिए", "बीसीए की फीस हेतु ऋण",
    "डिग्री पूरी करने के लिए लोन", "कॉलेज एडमिशन के बाद फीस चाहिए", "पोस्ट ग्रेजुएशन के लिए शिक्षा ऋण",
    "पढ़ाई जारी रखने के लिए चार लाख", "क्या NSFDC से शिक्षा लोन मिलेगा",
]
_EDU_ROMAN = [
    "mujhe padhai ke liye loan chahiye", "college fees bharne ke liye loan", "BTech ke liye char lakh chahiye",
    "higher education ka loan batao", "engineering padhai ke liye paisa", "MBBS ke liye education loan",
    "nursing course ki fees chahiye", "technical course ke liye rin", "diploma padhne ke liye loan",
    "university tuition ke liye finance", "pharmacy course loan", "MBA ki padhai ke liye paisa",
    "student education loan chahiye", "professional course ke liye finance", "BCA fees ke liye loan",
    "degree complete karne ka loan", "college admission fees ke liye loan", "post graduation ke liye education loan",
    "padhai jari rakhne ko char lakh", "NSFDC se education loan milega kya",
]

_BUS_EN = [
    "I need a loan to start a business", "Loan to open a small shop", "Finance for self employment",
    "I want working capital for my business", "Credit to start tailoring", "Loan for a repair workshop",
    "Money to open a salon", "Small enterprise loan", "I want to buy tools for my trade",
    "Loan to start catering", "Finance for a service business", "I need funds for a retail store",
    "Business startup finance", "Loan for a manufacturing unit", "Help me expand my small business",
    "Credit for an income generating activity", "I want to purchase a commercial vehicle",
    "Micro enterprise financing", "Loan to begin handicraft work", "Two lakh for my new business",
]
_BUS_HI = [
    "मुझे व्यवसाय शुरू करने के लिए लोन चाहिए", "दुकान खोलने के लिए ऋण", "स्वरोजगार के लिए पैसा चाहिए",
    "व्यवसाय के लिए कार्यशील पूंजी", "सिलाई का काम शुरू करने के लिए लोन", "मरम्मत की दुकान के लिए ऋण",
    "सैलून खोलने के लिए पैसा", "छोटे उद्यम के लिए लोन", "काम के औजार खरीदने हैं",
    "केटरिंग व्यवसाय शुरू करना है", "सेवा व्यवसाय के लिए वित्त", "खुदरा दुकान के लिए धन",
    "नया बिजनेस शुरू करने के लिए ऋण", "निर्माण इकाई के लिए लोन", "छोटा व्यवसाय बढ़ाना है",
    "आय वाला काम शुरू करने के लिए ऋण", "व्यावसायिक वाहन खरीदना है", "सूक्ष्म उद्यम के लिए वित्त",
    "हस्तशिल्प काम के लिए लोन", "नए बिजनेस के लिए दो लाख",
]
_BUS_ROMAN = [
    "mujhe business shuru karne ke liye loan chahiye", "dukaan kholne ke liye loan", "swarozgar ke liye paisa",
    "business ke liye working capital chahiye", "silai ka kaam shuru karna hai", "repair workshop ke liye rin",
    "salon kholne ke liye paisa", "small enterprise loan", "apne kaam ke tools kharidne hain",
    "catering business start karna hai", "service business ke liye finance", "retail shop ke liye paisa",
    "naya business startup loan", "manufacturing unit ke liye loan", "chhota business badhana hai mujhe",
    "income generating kaam ka loan", "commercial vehicle mujhe kharidna hai", "micro enterprise ke liye finance",
    "handicraft kaam ke liye loan", "naye business ke liye do lakh",
]

_AGR_EN = [
    "I need a loan for farming", "Finance for crop cultivation", "Loan to grow rice",
    "Credit for wheat farming", "Money for vegetable cultivation", "Agriculture activity loan",
    "I need finance for my farm", "Loan for horticulture work", "Credit for allied agriculture",
    "Funds to start crop production", "I need two lakh for farming", "Finance for farm inputs",
    "Loan for cultivation work", "Support for an income generating farm activity",
    "Agriculture self employment loan", "I want to grow crops commercially", "Farm enterprise finance",
    "Loan for seasonal cultivation", "Funding for a small agriculture project", "Credit for my crop business",
]
_AGR_HI = [
    "मुझे खेती के लिए लोन चाहिए", "फसल उगाने के लिए ऋण", "चावल की खेती के लिए पैसा",
    "गेहूं की खेती के लिए लोन", "सब्जी उगाने के लिए वित्त", "कृषि काम के लिए ऋण",
    "अपने खेत के लिए पैसा चाहिए", "बागवानी के लिए लोन", "कृषि से जुड़े काम के लिए ऋण",
    "फसल उत्पादन शुरू करना है", "खेती के लिए दो लाख चाहिए", "खेती की सामग्री के लिए वित्त",
    "खेती के काम के लिए लोन", "आय देने वाली कृषि गतिविधि के लिए ऋण", "कृषि स्वरोजगार के लिए पैसा",
    "व्यावसायिक फसल उगानी है", "कृषि उद्यम के लिए वित्त", "मौसमी खेती के लिए लोन",
    "छोटी कृषि परियोजना के लिए धन", "मेरे फसल व्यवसाय के लिए ऋण",
]
_AGR_ROMAN = [
    "mujhe kheti ke liye loan chahiye", "fasal ugane ke liye rin", "chawal ki kheti ke liye paisa",
    "gehun farming ka loan", "sabji ugane ke liye finance", "krishi kaam ke liye loan",
    "apne khet ke liye paisa", "bagwani ke liye loan", "agriculture allied kaam ka rin",
    "crop production shuru karna hai", "kheti ke liye do lakh", "farm inputs ke liye finance",
    "cultivation work ka loan", "income wali agriculture activity chahiye", "krishi self employment ka loan",
    "commercial fasal mujhe ugani hai", "farm enterprise ke liye finance", "seasonal cultivation ka loan",
    "small agriculture project ke liye funding", "meri crop business ke liye credit",
]

_LIVESTOCK = [
    ("en", "I want to start a dairy farm"), ("hi", "मुझे डेयरी फार्म शुरू करना है"),
    ("hi", "mujhe dairy ke liye loan chahiye"), ("en", "Loan for milk production"),
    ("hi", "दूध का व्यवसाय शुरू करने के लिए ऋण"), ("hi", "pashupalan ke liye finance"),
    ("en", "I need a poultry loan"), ("hi", "मुर्गी पालन के लिए लोन चाहिए"),
    ("hi", "murgi farm shuru karna hai"), ("en", "Finance for a poultry unit"),
    ("en", "Loan for goat rearing"), ("hi", "बकरी पालन के लिए ऋण"),
    ("hi", "bakri palan ka loan"), ("en", "Credit for livestock activity"),
    ("hi", "पशुधन व्यवसाय के लिए पैसा"), ("hi", "doodh dairy business ke liye finance"),
    ("en", "Small dairy enterprise finance"), ("hi", "डेयरी इकाई के लिए दो लाख"),
    ("hi", "poultry business ke liye paisa"), ("en", "Self employment loan for animal husbandry"),
]

_AMBIGUOUS = [
    "I need a loan", "Need money", "Can you help me?", "Which scheme is best?", "I need financial support",
    "मुझे लोन चाहिए", "पैसे चाहिए", "कोई योजना बताइए", "मेरी मदद कीजिए", "कौन सी स्कीम सही है",
    "mujhe loan chahiye", "paise chahiye", "koi scheme batao", "help karo", "mere liye kya hai",
    "two lakh", "दो लाख", "haan", "nahi", "Jaipur",
]


def _cases(group: str, language: str, queries: list[str], domain: str, schemes: tuple[str, ...], variant: str):
    return [
        EvalCase(f"{group}-{variant}-{i:02}", query, language, domain, "LOAN", schemes, group, variant)
        for i, query in enumerate(queries, 1)
    ]


SINGLE_TURN_CASES = [
    *_cases("education", "en", _EDU_EN, "EDUCATION", (EDUCATION_ID,), "english"),
    *_cases("education", "hi", _EDU_HI, "EDUCATION", (EDUCATION_ID,), "hindi"),
    *_cases("education", "hi", _EDU_ROMAN, "EDUCATION", (EDUCATION_ID,), "roman_hindi"),
    *_cases("business", "en", _BUS_EN, "BUSINESS", BUSINESS_IDS, "english"),
    *_cases("business", "hi", _BUS_HI, "BUSINESS", BUSINESS_IDS, "hindi"),
    *_cases("business", "hi", _BUS_ROMAN, "BUSINESS", BUSINESS_IDS, "roman_hindi"),
    *_cases("agriculture", "en", _AGR_EN, "AGRICULTURE", (TERM_ID,), "english"),
    *_cases("agriculture", "hi", _AGR_HI, "AGRICULTURE", (TERM_ID,), "hindi"),
    *_cases("agriculture", "hi", _AGR_ROMAN, "AGRICULTURE", (TERM_ID,), "roman_hindi"),
    *[
        EvalCase(f"livestock-{i:02}", query, lang, "AGRICULTURE", "LOAN", (TERM_ID,), "livestock", "mixed")
        for i, (lang, query) in enumerate(_LIVESTOCK, 1)
    ],
    *[
        EvalCase(
            f"ambiguous-{i:02}",
            query,
            "hi" if 6 <= i <= 19 and i != 16 else "en",
            None,
            None,
            (),
            "ambiguous",
        )
        for i, query in enumerate(_AMBIGUOUS, 1)
    ],
]

MULTI_TURN_CONVERSATIONS = [
    {
        "id": f"multi-{i:02}",
        "turns": turns,
        "domain": domain,
        "expected_scheme_ids": schemes,
    }
    for i, (turns, domain, schemes) in enumerate(
        [
            (["मुझे पढ़ाई के लिए लोन चाहिए", "BTech", "चार लाख", "जयपुर"], "EDUCATION", [EDUCATION_ID]),
            (["I need an education loan", "nursing", "₹3 lakh"], "EDUCATION", [EDUCATION_ID]),
            (["mujhe padhai ke liye loan chahiye", "MBA", "do lakh"], "EDUCATION", [EDUCATION_ID]),
            (["मुझे खेती के लिए लोन चाहिए", "फसल के लिए", "दो लाख"], "AGRICULTURE", [TERM_ID]),
            (["farming loan", "rice", "3 acres", "2 lakh"], "AGRICULTURE", [TERM_ID]),
            (["mujhe kheti ka loan chahiye", "dairy", "char lakh"], "AGRICULTURE", [TERM_ID]),
            (["business loan", "shop", "2 lakh"], "BUSINESS", list(BUSINESS_IDS)),
            (["mujhe business shuru karna hai", "tailoring", "one lakh"], "BUSINESS", list(BUSINESS_IDS)),
            (["दुकान खोलनी है", "दो लाख", "जयपुर"], "BUSINESS", list(BUSINESS_IDS)),
            (["education loan", "BTech", "farming loan", "crop"], "AGRICULTURE", [TERM_ID]),
            (["खेती के लिए लोन", "मुझे पढ़ाई के लिए लोन चाहिए", "MBBS"], "EDUCATION", [EDUCATION_ID]),
            (["business ke liye loan", "education ke liye bhi loan", "BCA"], "EDUCATION", [EDUCATION_ID]),
            (["dairy loan", "2 lakh", "haan"], "AGRICULTURE", [TERM_ID]),
            (["college loan", "diploma", "nahi"], "EDUCATION", [EDUCATION_ID]),
            (["agriculture finance", "poultry", "Jaipur"], "AGRICULTURE", [TERM_ID]),
            (["loan for studies", "pharmacy", "four lakh"], "EDUCATION", [EDUCATION_ID]),
            (["self employment loan", "repair shop", "three lakh"], "BUSINESS", list(BUSINESS_IDS)),
            (["खेती ऋण", "मेरे पास तीन एकड़ जमीन है", "फसल"], "AGRICULTURE", [TERM_ID]),
            (["padhai ka loan", "BTech", "char lakh", "haan"], "EDUCATION", [EDUCATION_ID]),
            (["shop loan", "2 lakh", "education loan", "MBA"], "EDUCATION", [EDUCATION_ID]),
        ],
        1,
    )
]

VOICE_LIKE_CASES = [
    "Farming", "खेती", "kheti", "BTech", "बीटेक", "dairy", "डेयरी", "poultry", "मुर्गी",
    "shop", "दुकान", "business", "पढ़ाई", "padhai", "crop", "फसल", "rice", "चावल", "education", "college",
]

assert len(SINGLE_TURN_CASES) == 220
assert len(MULTI_TURN_CONVERSATIONS) == 20
assert len(VOICE_LIKE_CASES) == 20
