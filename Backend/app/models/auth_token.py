from app.core.datetime_utils import utcnow
from app.extensions import db
from app.models.base import BigId


class EnlaceActivacion(db.Model):
    """HU_05 / HU_10: enlace para definir contraseña (vigencia 48 h). Solo se guarda el hash."""

    __tablename__ = "enlace_activacion"

    id = db.Column(BigId, primary_key=True)
    colaborador_id = db.Column(BigId, db.ForeignKey("colaborador.id"), nullable=False, index=True)
    token_hash = db.Column(db.String(255), nullable=False, unique=True)
    vence_en = db.Column(db.DateTime(timezone=True), nullable=False)
    usado_en = db.Column(db.DateTime(timezone=True))
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)