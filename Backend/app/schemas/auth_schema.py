"""Esquemas de autenticación (HU_01)."""
from marshmallow import EXCLUDE, Schema, fields, pre_load, validate

from app.core.errors import MSG_REQUIRED
from app.core.validators import not_blank

_REQ = {"required": MSG_REQUIRED, "null": MSG_REQUIRED, "invalid": "Valor no válido"}


class LoginSchema(Schema):
    """Ambos campos son obligatorios (RG-09). No se valida el formato del correo: un correo mal
    formado simplemente no coincide con ninguna cuenta y recibe el mismo mensaje genérico."""

    class Meta:
        unknown = EXCLUDE

    correo_institucional = fields.String(
        required=True,
        validate=[not_blank, validate.Length(max=254, error="Máximo 254 caracteres")],
        error_messages=_REQ,
    )
    password = fields.String(
        required=True,
        validate=[not_blank, validate.Length(max=128, error="Máximo 128 caracteres")],
        error_messages=_REQ,
    )

    @pre_load
    def normalize(self, data, **_kwargs):
        if isinstance(data, dict) and isinstance(data.get("correo_institucional"), str):
            data = {**data, "correo_institucional": data["correo_institucional"].strip().lower()}
        return data  # la contraseña nunca se recorta ni se modifica


class SessionUserSchema(Schema):
    """Datos mínimos del usuario en sesión (el frontend arma el menú por rol)."""

    id = fields.Integer()
    nombre_completo = fields.String()
    correo_institucional = fields.String()
    rol = fields.String()
    grado_escalafon = fields.String()