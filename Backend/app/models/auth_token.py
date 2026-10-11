from app.core.datetime_utils import utcnow
from app.extensions import db
from app.models.base import BigId, InetType


class EnlaceActivacion(db.Model):
    """HU_05 / HU_10: enlace para definir contraseña (vigencia 48 h). Solo se guarda el hash."""

    __tablename__ = "enlace_activacion"

    id = db.Column(BigId, primary_key=True)
    colaborador_id = db.Column(BigId, db.ForeignKey("colaborador.id"), nullable=False, index=True)
    token_hash = db.Column(db.String(255), nullable=False, unique=True)
    vence_en = db.Column(db.DateTime(timezone=True), nullable=False)
    usado_en = db.Column(db.DateTime(timezone=True))
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)

class IntentoLogin(db.Model):
    """HU_01: cada intento de inicio de sesión. Base del bloqueo (5 fallos consecutivos -> 15 min)."""

    __tablename__ = "intento_login"

    id = db.Column(BigId, primary_key=True)
    colaborador_id = db.Column(BigId, db.ForeignKey("colaborador.id"))  # NULL si el correo no existe
    correo = db.Column(db.String(254), nullable=False)
    exitoso = db.Column(db.Boolean, nullable=False)
    ip = db.Column(InetType)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (db.Index("ix_intento_login_correo_fecha", db.func.lower(correo), created_at.desc()),)