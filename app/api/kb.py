import re

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from app.auth.deps import audit, require
from app.auth.permissions import Permission
from app.db.session import get_session
from app.models import db
from app.models.enums import Category
from app.models.schemas import KBArticle

router = APIRouter(prefix="/kb", tags=["knowledge base"])
KB_ID = re.compile(r"^KB-\d{3}$")


class ArticleIn(BaseModel):
    category: Category
    title: str = Field(min_length=3, max_length=200)
    body: str = Field(min_length=20, max_length=8000)
    title_ar: str = Field(default="", max_length=200)
    body_ar: str = Field(default="", max_length=8000)
    policy_tags: list[str] = []


def _out(r: db.KbArticleRow) -> dict:
    return r.model_dump(mode="json")


def _reindex(row: db.KbArticleRow) -> None:
    from app.rag.store import upsert_article
    upsert_article(KBArticle(id=row.id, category=row.category, title=row.title, body=row.body,
                             title_ar=row.title_ar, body_ar=row.body_ar, policy_tags=row.policy_tags or []))


@router.get("")
def list_articles(_: db.User = Depends(require(Permission.TICKETS_VIEW)), session: Session = Depends(get_session)):
    return [_out(r) for r in session.exec(select(db.KbArticleRow).order_by(db.KbArticleRow.id)).all()]


@router.get("/{article_id}")
def get_article(article_id: str, _: db.User = Depends(require(Permission.TICKETS_VIEW)),
                session: Session = Depends(get_session)):
    row = session.get(db.KbArticleRow, article_id)
    if row is None:
        raise HTTPException(404, "article not found")
    return _out(row)


@router.put("/{article_id}")
def save_article(article_id: str, body: ArticleIn, request: Request,
                 user: db.User = Depends(require(Permission.KB_MANAGE)), session: Session = Depends(get_session)):
    """Create or update an article, then re-embed just that article (both languages)."""
    if not KB_ID.match(article_id):
        raise HTTPException(422, "Article IDs look like KB-031")
    row = session.get(db.KbArticleRow, article_id)
    created = row is None
    if created:
        row = db.KbArticleRow(id=article_id, **body.model_dump(mode="json"))
        session.add(row)
    else:
        for k, v in body.model_dump(mode="json").items():
            setattr(row, k, v)
    row.updated_by, row.updated_at = user.id, db._now()
    audit(session, user, "kb.create" if created else "kb.update", "kb", article_id, request, title=body.title)
    session.commit()
    session.refresh(row)
    try:
        _reindex(row)
    except Exception as e:  # saved, but search index is stale: tell the editor
        raise HTTPException(502, f"Saved, but re-indexing failed ({e}). Is Ollama running?")
    return _out(row)
