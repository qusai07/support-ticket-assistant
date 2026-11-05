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
    # ---- "needs a person" signals (found by the full eval: EV-27/28/29/44/49 were auto-sent).
    # They don't escalate; they block auto-send (see hitl.policy_review_reasons). Arabic regexes
    # are written in normalized form (ة->ه, أ->ا, ى->ي) because they run on normalize(text).
    "account_recovery": [
        r"(2fa|two[- ]factor|two[- ]step|authenticator|backup codes?).{0,80}(lost|locked|can'?t|cannot|no (longer|access)|don'?t have|new phone)",
        r"(lost|locked|can'?t|cannot|no (longer|access)|new phone|don'?t have).{0,80}(2fa|two[- ]factor|two[- ]step|authenticator|backup codes?)",
        r"locked out of (my )?account"],
    # A request for US to change the login email to a given address = account-takeover pattern (KB-027).
    # "How do I change my email?" (self-service how-to) does not match: it has no target address.
    "account_change_request": [
        r"(change|update|switch|replace|move)\b.{0,50}\be-?mail\b.{0,60}\bto\s+[\w.+-]+@[\w-]+\.\w+",
        r"(غير|تغيير|حدث|تحديث|بدل|تبديل).{0,40}(الايميل|البريد|ايميلي|بريدي).{0,60}[\w.+-]+@[\w-]+\.\w+"],
    "churn_risk": [
        r"\bcancel(l?ing)?\b.{0,25}\b(membership|subscription)\b",
        r"\b(third|fourth|fifth|\d+(st|nd|rd|th)) time\b", r"\bkeep (writing|contacting|emailing)\b",
        r"\bswitch(ing)? to (a |another )?(competitor|different (brand|company))",
        r"\bnever (buy|order|shop)\w* .{0,30}again"],
    "address_change": [
        r"(change|update|correct|fix|edit)\b.{0,30}\b(?<!email )(?<!e-mail )address\b", r"\bwrong address\b",
        r"(غير|تغيير|تعديل|اعدل|اغير|بدل|تبديل).{0,20}العنوان", r"عنوان (غلط|خطا)"],
    # Retroactive promo = a manual price adjustment. "Can I use two promo codes?" (a policy question) does not match.
    "promo_adjustment": [
        r"(promo|coupon|discount|voucher)( code)?.{0,40}(didn'?t|did not|wasn'?t|was not|not|never|failed).{0,15}(appl|work)",
        r"forgot (to (use|apply|enter) )?(my |the )?(promo|coupon|discount|voucher)",
        r"(كود|كوبون|بروموكود).{0,30}(ما|لم|مش|ماش).{0,10}(انطبق|اشتغل|تطبق|يشتغل|يتطبق|ينطبق)",
        r"نسيت.{0,15}(الكود|الكوبون|كود)"],
    "warranty_claim": [r"\bwarrant(y|ies)\b", r"\bguarantee\b", r"ضمان", r"كفاله"],
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
    "account_recovery": ["التحقق بخطوتين", "المصادقه الثنائيه", "ضاع جوالي", "ضاع تلفوني", "ضاع موبايلي",
                         "انقفل حسابي", "قفل حسابي", "ما اقدر ادخل حسابي", "مش قادر ادخل", "رموز الاحتياط"],
    "churn_risk": ["ثالث مره", "المره الثالثه", "للمره الثالثه", "رابع مره", "الغي اشتراكي", "الغي العضويه",
                   "الغي عضويتي", "الغاء الاشتراك", "الغاء العضويه", "ما راح اتعامل معكم", "مش هتعامل معاكم",
                   "اخر مره اشتري"],
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
        if any(re.search(p, t) for p in SIGNAL_PATTERNS[name]) or any(x in t for x in _AR_SIGNAL_NORM.get(name, [])):
            found.append(name)
    return found


def anger_cue_count(text: str, ignore_caps: bool = False) -> int:
    """Independent lexical anger cues: each distinct insult word (EN/AR), 2+ fully-capitalized
    words, and '!!'. ignore_caps: injection payloads ("SYSTEM OVERRIDE") use capitals without anger."""
    t = normalize(text)
    n = sum(bool(re.search(p, t)) for p in ANGER_WORDS) + sum(x in t for x in _AR_ANGER_NORM)
    n += "!!" in text
    if not ignore_caps:
        n += len([w for w in re.findall(r"\b[A-Z]{3,}\b", text) if not w.startswith("ORD")]) >= 2
    return n


def has_anger_cues(text: str, ignore_caps: bool = False) -> bool:
    return anger_cue_count(text, ignore_caps) >= 1


# 2+ independent cues = strong anger. The 3B model under-rates Arabic anger (EV-59: "اسوا شركه
# ... نصابين!!" scored only "negative"), so strong lexical evidence can raise the sentiment.
STRONG_ANGER_CUES = 2


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
