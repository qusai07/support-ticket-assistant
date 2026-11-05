"""Role-based access control.

Design:
- Roles are fixed (admin, lead, agent, analyst); their permission SETS are editable by
  admins from the UI (stored in role_permissions). Code defaults apply until edited.
- Endpoints check PERMISSIONS, never role names.
- Safety: the admin role always has every permission and cannot be edited, so no
  configuration can lock everyone out.
- Team scoping is separate from permissions (see app/auth/deps.py).
- Lookups are cached for a few seconds: an edit reaches every process (API, worker)
  within CACHE_TTL_S without a restart.
"""
import time
from enum import Enum


class Role(str, Enum):
    admin = "admin"
    lead = "lead"        # team lead / supervisor
    agent = "agent"      # support agent
    analyst = "analyst"  # read-only analytics


class Permission(str, Enum):
    TICKETS_VIEW = "tickets:view"                # own team's tickets
    TICKETS_VIEW_ALL = "tickets:view_all"        # every team's tickets
    TICKETS_CREATE = "tickets:create"
    TICKETS_REVIEW = "tickets:review"            # approve / edit / reject drafts
    TICKETS_HANDLE_ESCALATED = "tickets:handle_escalated"
    TICKETS_REASSIGN = "tickets:reassign"        # move to another team / agent
    KB_MANAGE = "kb:manage"
    SETTINGS_MANAGE = "settings:manage"          # thresholds, models, routing rules
    USERS_MANAGE = "users:manage"                # users, roles & permissions, teams
    ANALYTICS_VIEW = "analytics:view"
    AUDIT_VIEW = "audit:view"


P = Permission
DEFAULT_ROLE_PERMISSIONS: dict[Role, frozenset[Permission]] = {
    Role.admin: frozenset(Permission),
    Role.lead: frozenset({P.TICKETS_VIEW, P.TICKETS_VIEW_ALL, P.TICKETS_CREATE, P.TICKETS_REVIEW,
                          P.TICKETS_HANDLE_ESCALATED, P.TICKETS_REASSIGN, P.KB_MANAGE, P.ANALYTICS_VIEW}),
    Role.agent: frozenset({P.TICKETS_VIEW, P.TICKETS_CREATE, P.TICKETS_REVIEW}),
    Role.analyst: frozenset({P.TICKETS_VIEW, P.TICKETS_VIEW_ALL, P.ANALYTICS_VIEW}),
}
ROLE_PERMISSIONS = DEFAULT_ROLE_PERMISSIONS  # backwards-compatible name

# Default teams (seeded into the `teams` table on first run).
DEFAULT_TEAMS: list[tuple[str, str]] = [
    ("Product Safety", "سلامة المنتجات"), ("Legal & Compliance", "الشؤون القانونية والامتثال"),
    ("Account Security", "أمن الحسابات"), ("Billing Disputes", "نزاعات الفوترة"), ("VIP Care", "رعاية كبار العملاء"),
    ("Customer Care (Senior)", "خدمة العملاء (كبار الموظفين)"), ("Returns & Refunds", "الإرجاع والاسترداد"),
    ("Billing", "الفوترة"), ("Logistics", "الشحن والتوصيل"), ("Technical Support", "الدعم الفني"),
    ("Accounts", "الحسابات"), ("Customer Care", "خدمة العملاء"),
]
TEAMS = [n for n, _ in DEFAULT_TEAMS]

CACHE_TTL_S = 10
_cache: dict[str, frozenset[Permission]] = {}
_cache_at = 0.0


def _load() -> dict[str, frozenset[Permission]]:
    global _cache, _cache_at
    if _cache and time.monotonic() - _cache_at < CACHE_TTL_S:
        return _cache
    out = {r.value: perms for r, perms in DEFAULT_ROLE_PERMISSIONS.items()}
    try:
        from sqlmodel import Session, select

        from app.db.session import engine
        from app.models import db
        with Session(engine) as s:
            for row in s.exec(select(db.RolePermissions)).all():
                if row.role != Role.admin.value and row.role in out:
                    out[row.role] = frozenset(Permission(p) for p in row.permissions if p in Permission._value2member_map_)
    except Exception:
        pass  # no DB / table yet: code defaults apply
    _cache, _cache_at = out, time.monotonic()
    return out


def invalidate_cache() -> None:
    global _cache_at
    _cache_at = 0.0


def has_permission(role: Role | str, perm: Permission) -> bool:
    return perm in _load().get(Role(role).value, frozenset())


def permissions_for(role: Role | str) -> list[str]:
    return sorted(p.value for p in _load().get(Role(role).value, frozenset()))


def team_names(active_only: bool = True) -> list[str]:
    try:
        from sqlmodel import Session, select

        from app.db.session import engine
        from app.models import db
        with Session(engine) as s:
            q = select(db.TeamRow)
            if active_only:
                q = q.where(db.TeamRow.is_active)
            rows = s.exec(q.order_by(db.TeamRow.name)).all()
            if rows:
                return [r.name for r in rows]
    except Exception:
        pass
    return list(TEAMS)


def seed_teams() -> None:
    from sqlmodel import Session, select

    from app.db.session import engine
    from app.models import db
    with Session(engine) as s:
        if s.exec(select(db.TeamRow)).first() is None:
            for name, name_ar in DEFAULT_TEAMS:
                s.add(db.TeamRow(name=name, name_ar=name_ar))
            s.commit()
