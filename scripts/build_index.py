"""Build the Chroma index, then check retrieval recall@3 in English, Arabic and Arabizi.

    python -m scripts.build_index
    # compare against the English-only baseline:
    #   EMBEDDING_MODEL=default CHROMA_DIR=storage/chroma_minilm python -m scripts.build_index
"""
from app.config import get_settings
from app.rag.store import build_index, search_kb

print(f"Embedding model: {get_settings().embedding_model}")
print("Indexed:", build_index())

checks = {
    "en": {
        "I was charged twice for my order": "KB-002",
        "can I return the open box earbuds": "KB-007",
        "my power bank is smoking and swollen": "KB-023",
        "tracking says my package is lost": "KB-015",
        "camera shows offline in the app": "KB-021",
        "how do I delete my account": "KB-028",
    },
    "ar": {
        "انخصم المبلغ مرتين على نفس الطلب": "KB-002",
        "عايزة أرجع سماعات مفتوحة العلبة": "KB-007",
        "الباور بانك طلع منه دخان وانتفخ": "KB-023",
        "شركة الشحن قالت إن الطرد ضاع": "KB-015",
        "الكاميرا تظهر غير متصلة في التطبيق": "KB-021",
        "كيف أحذف حسابي وبياناتي؟": "KB-028",
        "بدي أعرف شو طرق الدفع اللي بتقبلوها": "KB-001",
        "ما وصلني رابط تغيير كلمة السر": "KB-025",
    },
    "arabizi/mixed": {
        "ana et5asamt marteen 3ala nafs el order": "KB-002",
        "el power bank tala3 meno dokhan": "KB-023",
        "el camera offline 3ala tool fel app": "KB-021",
        "بدي أعمل return للسماعات": "KB-006",
    },
}

total = hits = 0
for group, qs in checks.items():
    g_hits = 0
    print(f"\n--- {group}")
    for q, expected in qs.items():
        lang = "ar" if any("؀" <= ch <= "ۿ" for ch in q) else "en"
        top = search_kb(q, k=3, lang=lang)
        ok = expected in [d.source_id for d in top]
        g_hits += ok
        print(f"{'OK  ' if ok else 'MISS'} {q[:45]:<45} -> {[(d.source_id, d.lang, d.score) for d in top]}")
    print(f"recall@3 [{group}]: {g_hits}/{len(qs)}")
    total += len(qs)
    hits += g_hits
print(f"\nrecall@3 overall: {hits}/{total}")
