from app.core.datetime_utils import utcnow
from app.extensions import db
from app.models.base import BigId, SoftDeleteMixin, TimestampMixin


class TemporizadorActivo(TimestampMixin, SoftDeleteMixin, db.Model):
    """Un temporizador en curso por colaborador (módulo 8). HU_04 consulta si existe antes del logout."""

    __tablename__ = "temporizador_activo"

    id = db.Column(BigId, primary_key=True)
    colaborador_id = db.Column(
        BigId, db.ForeignKey("colaborador.id"), nullable=False, unique=True, index=True
    )
    # Sin FK a tarea: esa entidad llega con el módulo de tareas; el id igual se guarda.
    tarea_id = db.Column(BigId)
    iniciado_en = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
