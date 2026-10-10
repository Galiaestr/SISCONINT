from app.core.datetime_utils import utcnow
from app.extensions import db
from app.models.base import BigId, JsonType


class BitacoraAuditoria(db.Model):
    """RG-13. Tabla de solo inserción (la base bloquea UPDATE y DELETE con un trigger)."""

    __tablename__ = "bitacora_auditoria"

    id = db.Column(BigId, primary_key=True)
    usuario_id = db.Column(BigId, db.ForeignKey("colaborador.id"))
    entidad = db.Column(db.String(60), nullable=False)
    entidad_id = db.Column(BigId)
    accion = db.Column(db.String(10), nullable=False)  # CREAR | MODIFICAR | ELIMINAR | ESTATUS
    detalle = db.Column(JsonType)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)