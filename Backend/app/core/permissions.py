"""Roles y matriz de permisos (RG-01, RG-02). El backend es la fuente de verdad."""
from functools import wraps

from flask import g
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request

from app.core.errors import ForbiddenError, UnauthorizedError
from app.extensions import db
from app.models.user import (
    ROL_ADMINISTRADOR,
    ROL_CONTADOR,
    ROL_COORDINADOR,
    ROL_DUENO,
    ROLES,
    Colaborador,
)

# Permiso -> roles que lo tienen. El Dueño figura en todos (hereda Administrador y Coordinador).
PERMISSIONS: dict[str, frozenset[str]] = {
    "user:create": frozenset({ROL_DUENO, ROL_ADMINISTRADOR}),  # HU_05
}

# Roles que cada rol puede asignar al registrar/editar colaboradores (HU_05, HU_08).
ASSIGNABLE_ROLES: dict[str, frozenset[str]] = {
    ROL_DUENO: frozenset(ROLES),
    ROL_ADMINISTRADOR: frozenset({ROL_COORDINADOR, ROL_CONTADOR}),
}


def has_permission(rol: str, permission: str) -> bool:
    return rol in PERMISSIONS.get(permission, frozenset())


def can_assign_role(actor_rol: str, target_rol: str) -> bool:
    return target_rol in ASSIGNABLE_ROLES.get(actor_rol, frozenset())


def load_current_user() -> Colaborador:
    """Usuario del JWT ya validado. 401 si la cuenta ya no existe o está desactivada."""
    try:
        user_id = int(get_jwt_identity())
    except (TypeError, ValueError):
        raise UnauthorizedError()
    user = db.session.get(Colaborador, user_id)
    if user is None or not user.activo:
        raise UnauthorizedError("Sesión no válida")
    return user


def login_required(fn):
    """Exige sesión válida (cookie o cabecera) y deja al usuario en g.current_user."""

    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        g.current_user = load_current_user()
        return fn(*args, **kwargs)

    return wrapper


def require_permission(permission: str):
    """Valida el JWT, carga al usuario en g.current_user y exige el permiso (RG-02)."""

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            user = load_current_user()
            if not has_permission(user.rol, permission):
                raise ForbiddenError()
            g.current_user = user
            return fn(*args, **kwargs)

        return wrapper

    return decorator
