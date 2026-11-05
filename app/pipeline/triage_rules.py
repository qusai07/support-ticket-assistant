"""Deterministic triage signals (regex) for English and Arabic. No LLM.

Why do this in addition to the LLM?
- High-stakes signals (legal, chargeback, safety, fraud) drive escalation. A small
  local model can miss a word, especially in Arabic; a regex never does. We take
  the UNION of both.
- Entity extraction for well-formed IDs (ORD-12345, $199.00) is a regex problem.

Arabic handling:
- Text and patterns are both normalized (alef/yaa/taa-marbuta variants, diacritics,
  tatweel, Arabic-Indic digits), so "إسترداد" and "استرداد" match the same rule.
- Arabic patterns are matched as substrings, not with \\b, because Arabic attaches
  prefixes to words: "والمحامي" (and the lawyer) must still match "محامي".
"""
import re

# ------------------------------------------------------------------ normalization
_AR_DIACRITICS = re.compile(r"[ؐ-ًؚ-ٰٟۖ-ۭـ]")  # tashkeel + tatweel
_AR_MAP = str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا", "ة": "ه", "ى": "ي", "ؤ": "و", "ئ": "ي",
                         **{chr(0x0660 + i): str(i) for i in range(10)},   # Arabic-Indic digits
                         **{chr(0x06F0 + i): str(i) for i in range(10)}})  # Persian digits
ARABIC_CHAR = re.compile(r"[؀-ۿݐ-ݿ]")
LATIN_CHAR = re.compile(r"[A-Za-z]")


def normalize(text: str) -> str:
    return _AR_DIACRITICS.sub("", text).translate(_AR_MAP).lower()


# ------------------------------------------------------------------ language
ARABIZI_WORDS = {"3ayez", "3ayza", "3awez", "3ndi", "3andi", "7aga", "ezay", "ezzay", "leh", "mesh", "msh",
                 "ana", "enta", "enty", "law", "sama7t", "shukran", "shokran", "ya3ni", "keda", "lsa", "lessa",
                 "fen", "feen", "wen", "wein", "bdi", "baddi", "ma3", "mafi", "ma7al", "5alas", "inshallah",
                 "habibi", "a3mel", "3amalt", "el", "elly", "wala", "bas", "kda", "7ad", "mafeesh", "mish"}


def detect_language(text: str) -> str:
    """'ar' | 'en' | 'mixed' (Arabic + English) | 'ar_latn' (Arabizi: Arabic in Latin letters)."""
    ar = len(ARABIC_CHAR.findall(text))
    la = len(LATIN_CHAR.findall(re.sub(r"\bORD-\d+\b", "", text, flags=re.I)))
    letters = ar + la
    if letters == 0:
        return "en"
    if ar / letters >= 0.7:
        return "ar"
    if ar / letters >= 0.15:
        return "mixed"
    words = re.findall(r"[a-z0-9']+", text.lower())
    arabizi = sum(w in ARABIZI_WORDS or bool(re.search(r"[a-z][2357][a-z]|^[2357][a-z]{2,}", w)) for w in words)
    return "ar_latn" if words and arabizi / len(words) >= 0.2 else "en"


# ------------------------------------------------------------------ signals
# English: regex with word boundaries. Arabic: normalized substrings.
SIGNAL_PATTERNS: dict[str, list[str]] = {
    "legal": [r"\blawyer", r"\battorney", r"\blegal action", r"\bsue\b", r"\blawsuit",
              r"consumer protection", r"\bgdpr\b", r"\bcourt\b",
              r"\bm[ou]?7am[iy]\b", r"\b2[ae]?d[ei]?ya\b", r"\bqad[ei]?ya\b"],  # Arabizi: lawyer, lawsuit
    "chargeback": [r"charge ?back", r"dispute (the|this) (charge|payment)", r"\bdispute with my bank"],
    "charged_twice": [r"charged twice", r"double[- ]charged", r"two charges", r"charged me twice"],
    "cancel": [r"\bcancel"],
    "safety": [r"\bsmok(e|ing)\b", r"\bfire\b", r"\bburn(ing|t|ed)?\b", r"\bswollen\b", r"\bswelling\b",
               r"overheat", r"\bexplod", r"\bsparks?\b", r"\bmelt", r"(very|extremely|too|really) hot\b",
               r"\bd[ou](kh|5)an\b", r"\b7ari(2|q)a\b", r"\bet?n?fa(kh|5)\b"],  # Arabizi: smoke, fire, swelled
    "fraud": [r"\bhack(ed|er)?\b", r"didn'?t place", r"\bunauthori[sz]ed\b", r"\bstolen account",
              r"password was changed"],
}

AR_SIGNAL_TERMS: dict[str, list[str]] = {
    "legal": ["محامي", "محامٍ", "رفع قضيه", "قضيه ضد", "ارفع قضيه", "دعوي قضائيه", "محكمه", "اجراء قانوني", "اجراءات قانونيه", "قانونيا",
              "حمايه المستهلك", "ساقاضي", "هقاضي", "راح اشتكي عليكم", "شكوي رسميه", "حمايه البيانات"],
    "chargeback": ["اعتراض على العمليه", "استرجاع المبلغ من البنك", "نزاع مع البنك", "شكوي للبنك",
                   "الغاء العمليه من البنك", "اعترض على الدفع"],
    "charged_twice": ["مرتين", "خصم مكرر", "دفعت مرتين", "خصم مزدوج"],
    "cancel": ["الغاء", "الغي", "كنسل"],
    "safety": ["دخان", "حريق", "احترق", "انتفخ", "منتفخ", "انتفاخ", "سخن جدا", "ساخن جدا", "سخونه شديده",
               "ذاب الكيبل", "ذاب الشاحن", "ساح", "انفجر", "شراره", "ريحه حريق"],  # not bare "ذاب": it is inside "عذاب"
    "fraud": ["اختراق", "مخترق", "تهكير", "اتهكر", "انهكر", "سرقه الحساب", "طلبات ما طلبتها",
              "طلبات لم اطلبها", "غير مصرح", "تغيير كلمه المرور", "تغيرت كلمه السر"],
}

INJECTION_PATTERNS = [
    r"ignore (all |any )?(the )?(previous|prior|above) (instructions|prompts?)",
    r"system (override|prompt)", r"developer mode", r"note to (the )?ai", r"you are now",
    r"set confidence", r"recommended_action", r"\bjailbreak", r"</?ticket>", r"act as (an? )?(admin|system)",
]
AR_INJECTION_TERMS = ["تجاهل التعليمات", "تجاهل كل التعليمات", "تجاهل جميع التعليمات", "انت الان",
                      "وضع المطور", "موجه النظام", "تعليمات النظام", "ملاحظه للذكاء الاصطناعي",
                      "ملاحظه للمساعد", "اطبع التعليمات"]

ANGER_WORDS = [r"\bworst\b", r"\buseless\b", r"\bdisgust", r"\bfurious\b", r"\bpathetic\b", r"\bscam\b",
               r"\bhorrible\b", r"\bterrible\b", r"\bincompetent\b", r"\bsick of\b", r"\bjoke\b"]
AR_ANGER_TERMS = ["اسوا", "زفت", "فاشلين", "نصابين", "حراميه", "مهزله", "قرف", "تافهين", "خدمه سيئه",
                  "حسبي الله", "مستفز", "بلا فايده", "ما تستحون"]

ORDER_ID_RE = re.compile(r"\bORD-\d{5}\b", re.IGNORECASE)
AMOUNT_RE = re.compile(r"\$\s?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?|\d+(?:\.\d{2})?)")
AR_AMOUNT_RE = re.compile(r"(\d+(?:\.\d{1,2})?)\s?(?:دولار|\$)")

# Signals that force P1 regardless of what the LLM says.
P1_SIGNALS = {"legal", "chargeback", "safety", "fraud"}

_AR_SIGNAL_NORM = {k: [normalize(t) for t in v] for k, v in AR_SIGNAL_TERMS.items()}
_AR_INJECTION_NORM = [normalize(t) for t in AR_INJECTION_TERMS]
_AR_ANGER_NORM = [normalize(t) for t in AR_ANGER_TERMS]


def detect_signals(text: str) -> list[str]:
    t = normalize(text)
    found = []
    for name in SIGNAL_PATTERNS:
        if any(re.search(p, t) for p in SIGNAL_PATTERNS[name]) or any(x in t for x in _AR_SIGNAL_NORM[name]):
            found.append(name)
    return found


def has_anger_cues(text: str, ignore_caps: bool = False) -> bool:
    """Lexical anger: insult words (EN/AR), 2+ fully-capitalized words, or '!!'.
    ignore_caps: injection payloads ("SYSTEM OVERRIDE") use capitals without anger."""
    t = normalize(text)
    if any(re.search(p, t) for p in ANGER_WORDS) or any(x in t for x in _AR_ANGER_NORM):
        return True
    if ignore_caps:
        return "!!" in text
    caps_words = [w for w in re.findall(r"\b[A-Z]{3,}\b", text) if not w.startswith("ORD")]
    return len(caps_words) >= 2 or "!!" in text


def detect_injection(text: str) -> bool:
    t = normalize(text)
    return any(re.search(p, t) for p in INJECTION_PATTERNS) or any(x in t for x in _AR_INJECTION_NORM)


def extract_order_ids(text: str) -> list[str]:
    return sorted({m.upper() for m in ORDER_ID_RE.findall(normalize(text))})


def extract_amounts(text: str) -> list[float]:
    t = normalize(text)  # also converts Arabic-Indic digits (٥٠٠ -> 500)
    found = [float(a.replace(",", "")) for a in AMOUNT_RE.findall(t)]
    found += [float(a) for a in AR_AMOUNT_RE.findall(t) if float(a) not in found]
    return found
