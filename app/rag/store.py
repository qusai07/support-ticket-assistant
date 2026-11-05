"""Chroma vector store: KB articles (bilingual) and resolved past tickets (English).

- KB = policy, the only citable source. Each article is embedded twice
  ("KB-006#en", "KB-006#ar"); results are de-duplicated by article ID and returned
  in the customer's language, so an Arabic ticket gets the Arabic policy text.
- Past tickets = precedent (hints), never cited.
- Embeddings: bge-m3 via Ollama (multilingual, strong on Arabic, cross-lingual).
  Set EMBEDDING_MODEL=default to fall back to Chroma's English-only MiniLM.
"""
import json
from functools import lru_cache

import chromadb
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction, OllamaEmbeddingFunction

from app.config import DATA_DIR, get_settings
from app.models.schemas import HistoricalTicket, KBArticle, RetrievedDoc

KB, PAST = "kb_articles", "past_tickets"  # Chroma requires names of 3+ chars
_SPACE = {"hnsw:space": "cosine"}


@lru_cache
def client() -> chromadb.ClientAPI:
    return chromadb.PersistentClient(path=get_settings().chroma_dir)


@lru_cache
def _embedder():
    s = get_settings()
    if s.embedding_model == "default":
        return DefaultEmbeddingFunction()
    return OllamaEmbeddingFunction(url=s.ollama_host, model_name=s.embedding_model, timeout=120)


def _collection(name: str):
    return client().get_or_create_collection(name, metadata=_SPACE, embedding_function=_embedder())


def load_kb() -> list[KBArticle]:
    """KB source of truth: the DB (editable from the UI). On first run the DB is
    seeded from data/kb_articles.json. Falls back to the JSON if there's no DB."""
    seed = [KBArticle.model_validate(x) for x in json.loads((DATA_DIR / "kb_articles.json").read_text("utf-8"))]
    try:
        from sqlmodel import Session, select

        from app.db.session import engine, init_db
        from app.models import db
        init_db()
        with Session(engine) as s:
            rows = s.exec(select(db.KbArticleRow).order_by(db.KbArticleRow.id)).all()
            if not rows:
                for a in seed:
                    s.add(db.KbArticleRow(**a.model_dump(mode="json")))
                s.commit()
                return seed
            return [KBArticle(id=r.id, category=r.category, title=r.title, body=r.body, title_ar=r.title_ar,
                              body_ar=r.body_ar, policy_tags=r.policy_tags or []) for r in rows]
    except Exception:
        return seed


def _kb_docs(a: KBArticle) -> tuple[list[str], list[str], list[dict]]:
    ids, docs, metas = [], [], []
    for lang, title, body in (("en", a.title, a.body), ("ar", a.title_ar, a.body_ar)):
        if body:
            ids.append(f"{a.id}#{lang}")
            docs.append(f"{title}\n{body}")
            metas.append({"source_id": a.id, "lang": lang, "title": title, "category": a.category.value})
    return ids, docs, metas


def upsert_article(a: KBArticle) -> None:
    """Re-embed one article after an edit (no full rebuild)."""
    col = _collection(KB)
    col.delete(ids=[f"{a.id}#en", f"{a.id}#ar"])
    ids, docs, metas = _kb_docs(a)
    if ids:
        col.add(ids=ids, documents=docs, metadatas=metas)


def build_index() -> dict[str, int]:
    """(Re)build both collections. Idempotent."""
    kb = load_kb()
    past = [HistoricalTicket.model_validate(x)
            for x in json.loads((DATA_DIR / "historical_tickets.json").read_text("utf-8"))]

    for name in (KB, PAST):
        try:
            client().delete_collection(name)
        except Exception:
            pass

    ids, docs, metas = [], [], []
    for a in kb:
        i, d, m = _kb_docs(a)
        ids += i
        docs += d
        metas += m
    _collection(KB).add(ids=ids, documents=docs, metadatas=metas)

    _collection(PAST).add(
        ids=[t.id for t in past],
        documents=[f"{t.subject}\n{t.body}\nResolution: {t.resolution}" for t in past],
        metadatas=[{"source_id": t.id, "lang": "en", "title": t.subject, "category": t.category.value,
                    "kb_refs": ",".join(t.kb_refs)} for t in past],
    )
    return {KB: len(ids), PAST: len(past)}


def search_kb(text: str, k: int = 3, lang: str = "en") -> list[RetrievedDoc]:
    """Top-k distinct articles, each returned in `lang` (falls back to English)."""
    col = _collection(KB)
    res = col.query(query_texts=[text], n_results=min(k * 4, col.count()))
    best: dict[str, float] = {}
    for meta, dist in zip(res["metadatas"][0], res["distances"][0]):
        sid = meta["source_id"]
        best[sid] = max(best.get(sid, -1.0), round(1 - dist, 3))
    top = sorted(best.items(), key=lambda kv: -kv[1])[:k]
    if not top:
        return []

    wanted = list(dict.fromkeys([f"{sid}#{lang}" for sid, _ in top] + [f"{sid}#en" for sid, _ in top]))
    got = col.get(ids=wanted)
    by_id = {i: (d, m) for i, d, m in zip(got["ids"], got["documents"], got["metadatas"])}
    out = []
    for sid, score in top:
        doc, meta = by_id.get(f"{sid}#{lang}") or by_id[f"{sid}#en"]
        out.append(RetrievedDoc(source_id=sid, source_type="kb", lang=meta["lang"], title=meta["title"],
                                snippet=doc, score=score))
    return out


def search_past_tickets(text: str, k: int = 3) -> list[RetrievedDoc]:
    res = _collection(PAST).query(query_texts=[text], n_results=k)
    return [RetrievedDoc(source_id=i, source_type="past_ticket", title=m["title"], snippet=d, score=round(1 - dist, 3))
            for i, d, m, dist in zip(res["ids"][0], res["documents"][0], res["metadatas"][0], res["distances"][0])]
