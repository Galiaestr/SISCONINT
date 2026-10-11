"""Excepciones de dominio y manejadores globales (contrato único de errores)."""
from math import ceil

from flask import jsonify
from marshmallow import ValidationError as MarshmallowValidationError
from werkzeug.exceptions import HTTPException

from app.extensions import jwt

MSG_FORBIDDEN = "No tienes permiso para esta acción"
MSG_REQUIRED = "Campo obligatorio"
MSG_INVALID_CREDENTIALS = "Correo o contraseña incorrectos"
MSG_ACCOUNT_DISABLED = "Cuenta desactivada. Contacta al Administrador"


class AppError(Exception):
    status = 400
    code = "BAD_REQUEST"
    default_message = "Solicitud no válida"

    def __init__(
        self,
        message: str | None = None,
        fields: dict | None = None,
        extra: dict | None = None,
    ):
        super().__init__(message or self.default_message)
        self.message = message or self.default_message
        self.fields = fields
        self.extra = extra


class ValidationAppError(AppError):
    status = 422
    code = "VALIDATION_ERROR"
    default_message = "Hay campos con errores"


class UnauthorizedError(AppError):
    status = 401
    code = "UNAUTHORIZED"
    default_message = "Sesión no válida"


class InvalidCredentialsError(UnauthorizedError):
    """Correo inexistente y contraseña incorrecta comparten el mismo mensaje."""

    code = "INVALID_CREDENTIALS"
    default_message = MSG_INVALID_CREDENTIALS


class ForbiddenError(AppError):
    status = 403
    code = "FORBIDDEN"
    default_message = MSG_FORBIDDEN


class AccountDisabledError(ForbiddenError):
    """La cuenta del colaborador está desactivada."""

    code = "ACCOUNT_DISABLED"
    default_message = MSG_ACCOUNT_DISABLED


class AccountLockedError(AppError):
    """Bloqueo temporal por intentos fallidos de inicio de sesión."""

    status = 423
    code = "ACCOUNT_LOCKED"

    def __init__(self, retry_after_seconds: int):
        minutes = max(1, ceil(retry_after_seconds / 60))
        unit = "minuto" if minutes == 1 else "minutos"

        super().__init__(
            f"Cuenta bloqueada por intentos fallidos. "
            f"Intenta de nuevo en {minutes} {unit}",
            extra={"retry_after_seconds": retry_after_seconds},
        )


class NotFoundError(AppError):
    status = 404
    code = "NOT_FOUND"
    default_message = "Recurso no encontrado"


class ConflictError(AppError):
    status = 409
    code = "CONFLICT"
    default_message = "Conflicto con el estado actual del recurso"


class TimerActiveError(ConflictError):
    """HU_04: no se cierra la sesión si el colaborador tiene un temporizador corriendo."""

    code = "TIMER_ACTIVE"
    default_message = (
        "Tienes un temporizador activo. Deténlo y guárdalo antes de cerrar sesión"
    )


def error_response(
    status: int,
    code: str,
    message: str,
    fields: dict | None = None,
    extra: dict | None = None,
):
    body: dict = {"error": {"code": code, "message": message}}
    if fields:
        body["error"]["fields"] = fields
    if extra:
        body["error"].update(extra)
    return jsonify(body), status


def _flatten_marshmallow(messages) -> dict:
    """Convierte los errores de Marshmallow a {campo: [mensajes]}."""
    fields: dict = {}
    if isinstance(messages, dict):
        for key, value in messages.items():
            fields[key] = value if isinstance(value, list) else [str(value)]
    else:
        fields["_schema"] = [str(m) for m in messages]
    return fields


def register_error_handlers(app):
    @app.errorhandler(AppError)
    def handle_app_error(err: AppError):
        response, status = error_response(
            err.status, err.code, err.message, err.fields, err.extra
        )
        if err.extra and "retry_after_seconds" in err.extra:
            response.headers["Retry-After"] = str(err.extra["retry_after_seconds"])
        return response, status

    @app.errorhandler(MarshmallowValidationError)
    def handle_validation_error(err: MarshmallowValidationError):
        return error_response(
            422,
            "VALIDATION_ERROR",
            "Hay campos con errores",
            _flatten_marshmallow(err.messages),
        )

    @app.errorhandler(HTTPException)
    def handle_http_exception(err: HTTPException):
        codes = {
            404: "NOT_FOUND",
            405: "METHOD_NOT_ALLOWED",
            415: "UNSUPPORTED_MEDIA_TYPE",
        }
        return error_response(
            err.code or 500,
            codes.get(err.code, "HTTP_ERROR"),
            err.description or err.name,
        )

    @app.errorhandler(Exception)
    def handle_unexpected(err: Exception):
        app.logger.exception("Error no controlado")
        return error_response(
            500, "INTERNAL_ERROR", "Ocurrió un error inesperado"
        )


def register_jwt_handlers():
    @jwt.unauthorized_loader
    def _missing(_reason):
        return error_response(401, "UNAUTHORIZED", "Inicia sesión para continuar")

    @jwt.invalid_token_loader
    def _invalid(_reason):
        return error_response(401, "UNAUTHORIZED", "Sesión no válida")

    @jwt.expired_token_loader
    def _expired(_header, _payload):
        return error_response(
            401, "SESSION_EXPIRED", "Tu sesión expiró. Inicia sesión de nuevo"
        )

    @jwt.revoked_token_loader
    def _revoked(_header, _payload):
        return error_response(401, "UNAUTHORIZED", "Sesión no válida")

    @jwt.token_in_blocklist_loader
    def _blocklisted(_header, payload: dict) -> bool:
        from app.core.security import jti_is_revoked

        return jti_is_revoked(payload.get("jti", ""))
