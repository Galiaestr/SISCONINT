"""RG-13: toda creación, modificación, eliminación y cambio de estatus deja rastro."""
from app.extensions import db
from app.models.audit_log import BitacoraAuditoria

CREAR = "CREAR"
MODIFICAR = "MODIFICAR"
ELIMINAR = "ELIMINAR"
ESTATUS = "ESTATUS"


def log(usuario_id: int | None, entidad: str, entidad_id: int | None, accion: str, detalle: dict | None = None):
    """Agrega el registro a la sesión actual; se confirma junto con la operación de negocio."""
    entry = BitacoraAuditoria(
        usuario_id=usuario_id, entidad=entidad, entidad_id=entidad_id, accion=accion, detalle=detalle
    )
    db.session.add(entry)
    return entry