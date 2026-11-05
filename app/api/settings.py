from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlmodel import Session

from app.auth.deps import audit, require
from app.auth.permissions import Permission
from app.db.session import get_session
from app.models import db
from app.runtime_settings import EDITABLE, defaults, get_runtime, validate

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("")
def read_settings(_: db.User = Depends(require(Permission.ANALYTICS_VIEW))):
    return {"values": get_runtime(force=True), "defaults": defaults(), "schema": EDITABLE}


class SettingsPatch(BaseModel):
    values: dict[str, Any]


@router.patch("")
def update_settings(body: SettingsPatch, request: Request, user: db.User = Depends(require(Permission.SETTINGS_MANAGE)),
                    session: Session = Depends(get_session)):
    try:
        clean = {k: validate(k, v) for k, v in body.values.items()}
    except ValueError as e:
        raise HTTPException(422, str(e))
    before = get_runtime(force=True)
    for k, v in clean.items():
        row = session.get(db.AppSetting, k)
        if row is None:
            session.add(db.AppSetting(key=k, value={"v": v}, updated_by=user.id))
        else:
            row.value, row.updated_by, row.updated_at = {"v": v}, user.id, db._now()
    audit(session, user, "settings.update", "settings", None, request,
          changes={k: {"from": before.get(k), "to": v} for k, v in clean.items()})
    session.commit()
    return {"values": get_runtime(force=True)}
