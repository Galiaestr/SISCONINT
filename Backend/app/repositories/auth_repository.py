from datetime import datetime

from sqlalchemy import func, select

from app.extensions import db
from app.models.auth_token import IntentoLogin


def add_attempt(correo: str, exitoso: bool, colaborador_id: int | None, ip: str | None) -> IntentoLogin:
    attempt = IntentoLogin(correo=correo, exitoso=exitoso, colaborador_id=colaborador_id, ip=ip)
    db.session.add(attempt)
    return attempt


def failure_streak(correo: str) -> tuple[int, datetime | None]:
    """Fallos consecutivos de un correo (desde su último inicio exitoso) y la fecha del último."""
    same_email = func.lower(IntentoLogin.correo) == correo.lower()

    last_ok = db.session.scalar(
        select(func.max(IntentoLogin.created_at)).where(same_email, IntentoLogin.exitoso.is_(True))
    )
    stmt = select(func.count(IntentoLogin.id), func.max(IntentoLogin.created_at)).where(
        same_email, IntentoLogin.exitoso.is_(False)
    )
    if last_ok is not None:
        stmt = stmt.where(IntentoLogin.created_at > last_ok)

    count, last_fail = db.session.execute(stmt).one()
    return count, last_fail
