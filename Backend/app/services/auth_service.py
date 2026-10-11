"""HU_01 / HU_04: inicio y cierre de sesión. Lógica de negocio, no conoce HTTP."""
from datetime import timedelta, timezone
from math import ceil

from flask import current_app

from app.core.datetime_utils import utcnow
from app.core.errors import (
    AccountDisabledError,
    AccountLockedError,
    InvalidCredentialsError,
    TimerActiveError,
)
from app.core.security import revoke_jti, verify_password
from app.extensions import db
from app.models.user import Colaborador
from app.repositories import auth_repository, user_repository
from app.services import time_service


def login(correo: str, password: str, ip: str | None) -> Colaborador:
    """Valida credenciales y devuelve al colaborador. Lanza:

    - AccountLockedError (423): 5 fallos consecutivos; bloqueo de 15 min con tiempo restante.
    - InvalidCredentialsError (401): correo inexistente, sin contraseña o contraseña incorrecta
      (mismo mensaje en todos los casos).
    - AccountDisabledError (403): credenciales correctas pero cuenta Inactiva.
    """
    correo = correo.strip().lower()

    remaining = _lock_remaining_seconds(correo)
    if remaining > 0:
        # Mientras dure el bloqueo no se verifica ni se registra nada (ni con la contraseña correcta).
        raise AccountLockedError(remaining)

    user = user_repository.get_by_email(correo)
    # Siempre se verifica un hash (real o ficticio) para no revelar por tiempo qué correos existen.
    valid = verify_password(user.password_hash if user else None, password)

    if user is None or not valid:
        auth_repository.add_attempt(correo, False, user.id if user else None, ip)
        db.session.commit()
        remaining = _lock_remaining_seconds(correo)  # ¿este fallo fue el que activó el bloqueo?
        if remaining > 0:
            raise AccountLockedError(remaining)
        raise InvalidCredentialsError()

    # Solo se revela que la cuenta está desactivada a quien conoce la contraseña.
    if not user.activo:
        raise AccountDisabledError()

    auth_repository.add_attempt(correo, True, user.id, ip)  # un éxito reinicia la racha de fallos
    db.session.commit()
    return user


def logout(
    user_id: int,
    access_jti: str,
    access_exp: int,
    refresh_jti: str | None = None,
    refresh_exp: int | None = None,
) -> None:
    """HU_04: invalida de inmediato el access (y el refresh, si viene) en la lista de revocados.

    Si hay temporizador activo no se revoca nada: el cliente debe detenerlo y guardarlo antes.
    """
    if time_service.get_active_timer(user_id):
        raise TimerActiveError()

    revoke_jti(access_jti, _ttl_seconds(access_exp))
    if refresh_jti and refresh_exp:
        revoke_jti(refresh_jti, _ttl_seconds(refresh_exp))


def _ttl_seconds(exp: int) -> int:
    return max(1, int(exp - utcnow().timestamp()))


def _lock_remaining_seconds(correo: str) -> int:
    """Segundos de bloqueo que faltan (0 si no está bloqueado).

    Los intentos hechos durante un bloqueo no se registran, así que la racha de fallos crece de
    5 en 5: está bloqueado cuando la racha es múltiplo de 5 y el último fallo fue hace menos de
    15 min. Al vencer el bloqueo se permiten otros 5 intentos.
    """
    cfg = current_app.config
    count, last_fail = auth_repository.failure_streak(correo)
    if not count or last_fail is None or count % cfg["LOGIN_MAX_ATTEMPTS"] != 0:
        return 0
    if last_fail.tzinfo is None:  # SQLite devuelve fechas sin zona; en PostgreSQL ya vienen con ella
        last_fail = last_fail.replace(tzinfo=timezone.utc)
    locked_until = last_fail + timedelta(minutes=cfg["LOGIN_LOCK_MINUTES"])
    return max(0, ceil((locked_until - utcnow()).total_seconds()))