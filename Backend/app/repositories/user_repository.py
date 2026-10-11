from sqlalchemy import func, select

from app.extensions import db
from app.models.auth_token import EnlaceActivacion
from app.models.user import Colaborador


def get_by_email(correo: str) -> Colaborador | None:
    return db.session.execute(
        select(Colaborador).where(
            func.lower(Colaborador.correo_institucional) == correo.lower(),
            Colaborador.deleted_at.is_(None),
        )
    ).scalar_one_or_none()


def email_exists(correo: str) -> bool:
    """Compara sin distinguir mayúsculas e incluye eliminados: el índice único de la base los cuenta."""
    stmt = select(Colaborador.id).where(func.lower(Colaborador.correo_institucional) == correo.lower()).limit(1)
    return db.session.execute(stmt).first() is not None


def add(user: Colaborador) -> Colaborador:
    db.session.add(user)
    db.session.flush()  # obtiene user.id sin confirmar
    return user


def add_activation_link(link: EnlaceActivacion) -> EnlaceActivacion:
    db.session.add(link)
    return link