from app.extensions import db
from app.core.datetime_utils import utcnow
from app.models.base import BigId, SoftDeleteMixin, TimestampMixin

# Valores (coinciden con los CHECK de la tabla colaborador)
ROL_DUENO = "DUENO"
ROL_ADMINISTRADOR = "ADMINISTRADOR"
ROL_COORDINADOR = "COORDINADOR"
ROL_CONTADOR = "CONTADOR"
ROLES = (ROL_DUENO, ROL_ADMINISTRADOR, ROL_COORDINADOR, ROL_CONTADOR)

GRADOS = ("JUNIOR", "SENIOR", "ADMIN")

ESTATUS_ACTIVO = "ACTIVO"
ESTATUS_INACTIVO = "INACTIVO"


class Colaborador(TimestampMixin, SoftDeleteMixin, db.Model):
    __tablename__ = "colaborador"

    id = db.Column(BigId, primary_key=True)
    nombre_completo = db.Column(db.String(150), nullable=False)
    correo_institucional = db.Column(db.String(254), nullable=False)
    password_hash = db.Column(db.String(255))  # NULL hasta que active la cuenta
    rol = db.Column(db.String(15), nullable=False)
    grado_escalafon = db.Column(db.String(10), nullable=False)
    estatus = db.Column(db.String(10), nullable=False, default=ESTATUS_ACTIVO)
    telefono_despacho = db.Column(db.String(10), nullable=False)
    telefono_personal = db.Column(db.String(10), nullable=False)
    licenciatura = db.Column(db.String(150))
    cedula = db.Column(db.String(8))
    calle = db.Column(db.String(150))
    no_ext_int = db.Column(db.String(40))
    colonia = db.Column(db.String(100))
    municipio = db.Column(db.String(100))
    estado = db.Column(db.String(100))
    emergencia_nombre = db.Column(db.String(150), nullable=False)
    emergencia_telefono = db.Column(db.String(10), nullable=False)
    fecha_alta = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    created_by = db.Column(BigId, db.ForeignKey("colaborador.id"))
    updated_by = db.Column(BigId, db.ForeignKey("colaborador.id"))

    __table_args__ = (
        # Único sin distinguir mayúsculas (igual que uq_colaborador_correo en PostgreSQL).
        db.Index("uq_colaborador_correo", db.func.lower(correo_institucional), unique=True),
    )

    @property
    def activo(self) -> bool:
        return self.estatus == ESTATUS_ACTIVO and self.deleted_at is None