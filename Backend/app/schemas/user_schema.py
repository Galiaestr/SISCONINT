"""Esquemas de entrada/salida de colaboradores (HU_05)."""
from marshmallow import EXCLUDE, Schema, fields, pre_load, validate

from app.core.errors import MSG_REQUIRED
from app.core.validators import not_blank, validate_cedula, validate_email, validate_phone
from app.models.user import GRADOS, ROLES

_REQ = {"required": MSG_REQUIRED, "null": MSG_REQUIRED, "invalid": "Valor no válido"}
_OPT = {"invalid": "Valor no válido"}


def _required(max_len: int, *extra):
    return fields.String(
        required=True, validate=[not_blank, validate.Length(max=max_len, error=f"Máximo {max_len} caracteres"), *extra],
        error_messages=_REQ,
    )


def _optional(max_len: int, *extra):
    return fields.String(
        load_default=None, allow_none=True,
        validate=[validate.Length(max=max_len, error=f"Máximo {max_len} caracteres"), *extra],
        error_messages=_OPT,
    )


class ColaboradorCreateSchema(Schema):
    """Campos obligatorios (*): nombre, teléfono despacho, correo, rol, grado, teléfono personal,
    nombre y teléfono de emergencia. El resto es opcional."""

    class Meta:
        unknown = EXCLUDE

    nombre_completo = _required(150)
    telefono_despacho = _required(10, validate_phone)
    correo_institucional = _required(254, validate_email)
    rol = fields.String(
        required=True, error_messages=_REQ,
        validate=validate.OneOf(ROLES, error="Rol no válido. Valores: " + ", ".join(ROLES)),
    )
    grado_escalafon = fields.String(
        required=True, error_messages=_REQ,
        validate=validate.OneOf(GRADOS, error="Grado no válido. Valores: " + ", ".join(GRADOS)),
    )
    telefono_personal = _required(10, validate_phone)
    emergencia_nombre = _required(150)
    emergencia_telefono = _required(10, validate_phone)

    licenciatura = _optional(150)
    cedula = _optional(8, validate_cedula)
    calle = _optional(150)
    no_ext_int = _optional(40)
    colonia = _optional(100)
    municipio = _optional(100)
    estado = _optional(100)

    @pre_load
    def normalize(self, data, **_kwargs):
        if not isinstance(data, dict):
            return data
        clean = {}
        for key, value in data.items():
            if isinstance(value, str):
                value = value.strip()
                if value == "":
                    # Vacío = no enviado: en obligatorios da "Campo obligatorio"; en opcionales, NULL.
                    value = None
            clean[key] = value
        if isinstance(clean.get("correo_institucional"), str):
            clean["correo_institucional"] = clean["correo_institucional"].lower()
        for key in ("rol", "grado_escalafon"):
            if isinstance(clean.get(key), str):
                clean[key] = clean[key].upper()
        return clean


class ColaboradorSchema(Schema):
    """Salida: nunca incluye password_hash."""

    id = fields.Integer()
    nombre_completo = fields.String()
    correo_institucional = fields.String()
    rol = fields.String()
    grado_escalafon = fields.String()
    estatus = fields.String()
    telefono_despacho = fields.String()
    telefono_personal = fields.String()
    licenciatura = fields.String(allow_none=True)
    cedula = fields.String(allow_none=True)
    calle = fields.String(allow_none=True)
    no_ext_int = fields.String(allow_none=True)
    colonia = fields.String(allow_none=True)
    municipio = fields.String(allow_none=True)
    estado = fields.String(allow_none=True)
    emergencia_nombre = fields.String()
    emergencia_telefono = fields.String()
    fecha_alta = fields.DateTime()