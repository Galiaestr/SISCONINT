"""Excepciones de dominio y manejadores globales (contrato único de errores)."""
from flask import jsonify
from marshmallow import ValidationError as MarshmallowValidationError
from werkzeug.exceptions import HTTPException

from app.extensions import jwt

MSG_FORBIDDEN = "No tienes permiso para esta acción"  # RG-02
MSG_REQUIRED = "Campo obligatorio"  # RG-09


class AppError(Exception):
    status = 400
    code = "BAD_REQUEST"
    default_message = "Solicitud no válida"

    def __init__(self, message: str | None = None, fields: dict | None = None):
        super().__init__(message or self.default_message)
        self.message = message or self.default_message
        self.fields = fields


class ValidationAppError(AppError):
    status = 422
    code = "VALIDATION_ERROR"
    default_message = "Hay campos con errores"


class UnauthorizedError(AppError):
    status = 401
    code = "UNAUTHORIZED"
    default_message = "Sesión no válida"


class ForbiddenError(AppError):
    status = 403
    code = "FORBIDDEN"
    default_message = MSG_FORBIDDEN


class NotFoundError(AppError):
    status = 404
    code = "NOT_FOUND"
    default_message = "Recurso no encontrado"


class ConflictError(AppError):
    status = 409
    code = "CONFLICT"
    default_message = "Conflicto con el estado actual del recurso"


def error_response(status: int, code: str, message: str, fields: dict | None = None):
    body: dict = {"error": {"code": code, "message": message}}
    if fields:
        body["error"]["fields"] = fields
    return jsonify(body), status


def _flatten_marshmallow(messages) -> dict:
    """Convierte los errores de marshmallow a {campo: [mensajes]}."""
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
        return error_response(err.status, err.code, err.message, err.fields)

    @app.errorhandler(MarshmallowValidationError)
    def handle_validation_error(err: MarshmallowValidationError):
        return error_response(
            422, "VALIDATION_ERROR", "Hay campos con errores", _flatten_marshmallow(err.messages)
        )

    @app.errorhandler(HTTPException)
    def handle_http_exception(err: HTTPException):
        codes = {404: "NOT_FOUND", 405: "METHOD_NOT_ALLOWED", 415: "UNSUPPORTED_MEDIA_TYPE"}
        return error_response(err.code or 500, codes.get(err.code, "HTTP_ERROR"), err.description or err.name)

    @app.errorhandler(Exception)
    def handle_unexpected(err: Exception):
        app.logger.exception("Error no controlado")
        return error_response(500, "INTERNAL_ERROR", "Ocurrió un error inesperado")


def register_jwt_handlers():
    @jwt.unauthorized_loader
    def _missing(_reason):
        return error_response(401, "UNAUTHORIZED", "Inicia sesión para continuar")

    @jwt.invalid_token_loader
    def _invalid(_reason):
        return error_response(401, "UNAUTHORIZED", "Sesión no válida")

    @jwt.expired_token_loader
    def _expired(_header, _payload):
        return error_response(401, "SESSION_EXPIRED", "Tu sesión expiró. Inicia sesión de nuevo")