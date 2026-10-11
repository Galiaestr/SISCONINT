"""Lógica de negocio de colaboradores. No conoce HTTP."""
from datetime import timedelta

from flask import current_app
from sqlalchemy.exc import IntegrityError

from app.core import audit
from app.core.datetime_utils import utcnow
from app.core.errors import ConflictError, ForbiddenError
from app.core.permissions import can_assign_role
from app.core.security import generate_token
from app.extensions import db
from app.models.auth_token import EnlaceActivacion
from app.models.user import ESTATUS_ACTIVO, Colaborador
from app.repositories import user_repository

MSG_EMAIL_DUPLICATED = "El correo ya está registrado"


def register_user(actor: Colaborador, data: dict) -> tuple[Colaborador, str]:
    """HU_05. Crea el colaborador Activo y su enlace de activación.

    Devuelve (colaborador, token_en_claro). El token en claro solo existe aquí para armar el
    correo; en la base se guarda su hash.
    """
    # El Dueño asigna cualquier rol; el Administrador solo Coordinador o Contador.
    if not can_assign_role(actor.rol, data["rol"]):
        raise ForbiddenError("No puedes asignar el rol seleccionado")

    if user_repository.email_exists(data["correo_institucional"]):
        raise _duplicated_email()

    user = Colaborador(**data, estatus=ESTATUS_ACTIVO, created_by=actor.id, updated_by=actor.id)
    raw_token, token_hash = generate_token()
    hours = current_app.config["ACTIVATION_LINK_HOURS"]

    try:
        user_repository.add(user)
        user_repository.add_activation_link(
            EnlaceActivacion(colaborador_id=user.id, token_hash=token_hash, vence_en=utcnow() + timedelta(hours=hours))
        )
        audit.log(
            actor.id, "colaborador", user.id, audit.CREAR,
            {"rol": user.rol, "grado_escalafon": user.grado_escalafon, "correo_institucional": user.correo_institucional},
        )
        db.session.commit()
    except IntegrityError:
        # Carrera: otro registro con el mismo correo se confirmó entre la verificación y el INSERT.
        db.session.rollback()
        raise _duplicated_email()

    return user, raw_token


def _duplicated_email() -> ConflictError:
    return ConflictError(MSG_EMAIL_DUPLICATED, fields={"correo_institucional": [MSG_EMAIL_DUPLICATED]})