"""Módulo 1: Autenticación. Prefijo /api/v1/auth. Sesión en cookies httpOnly (JWT)."""
from flask import Blueprint, current_app, g, jsonify, request
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    jwt_required,
    set_access_cookies,
    set_refresh_cookies,
    unset_jwt_cookies,
)

from app.core.errors import ValidationAppError
from app.core.permissions import load_current_user, login_required
from app.schemas.auth_schema import LoginSchema, SessionUserSchema
from app.services import auth_service

bp = Blueprint("auth", __name__, url_prefix="/auth")


def _session_response(user):
    """Respuesta con los datos del usuario y las cookies de sesión (los tokens NO van en el cuerpo)."""
    cfg = current_app.config
    identity = str(user.id)
    response = jsonify({"data": SessionUserSchema().dump(user)})
    # max_age explícito: sin él las cookies serían de sesión de navegador o de un año.
    set_access_cookies(
        response, create_access_token(identity=identity),
        max_age=int(cfg["JWT_ACCESS_TOKEN_EXPIRES"].total_seconds()),
    )
    set_refresh_cookies(
        response, create_refresh_token(identity=identity),
        max_age=int(cfg["JWT_REFRESH_TOKEN_EXPIRES"].total_seconds()),
    )
    return response


@bp.post("/login")
def login():
    """HU_01: iniciar sesión con correo institucional y contraseña."""
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        raise ValidationAppError("El cuerpo de la petición debe ser un objeto JSON")

    data = LoginSchema().load(payload)  # RG-09: «Campo obligatorio»
    user = auth_service.login(data["correo_institucional"], data["password"], request.remote_addr)
    return _session_response(user)


@bp.post("/refresh")
@jwt_required(refresh=True)
def refresh():
    """Renueva access y refresh (ventana deslizante de 30 min, RG-06). Rechaza cuentas desactivadas."""
    return _session_response(load_current_user())


@bp.get("/me")
@login_required
def me():
    """Usuario en sesión (el frontend lo consulta al cargar para armar el menú según el rol)."""
    return jsonify({"data": SessionUserSchema().dump(g.current_user)})


@bp.post("/logout")
def logout():
    """Borra las cookies de sesión. La invalidación en servidor (lista de revocados) llega con HU_04."""
    response = jsonify({"data": {"message": "Sesión cerrada"}})
    unset_jwt_cookies(response)
    return response
