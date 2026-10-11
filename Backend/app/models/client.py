from app import db

class Client(db.Model):
    __tablename__ = 'cliente'

    id = db.Column(db.BigInteger, primary_key=True)
    nombre_completo = db.Column(db.Text, nullable=False)
    rfc = db.Column(db.Text, unique=True, nullable=False)
    tipo_persona = db.Column(db.Text, nullable=False)
    razon_social = db.Column(db.Text, nullable=True)
    forma_pago = db.Column(db.Text, nullable=False)
    contador_asignado_id = db.Column(db.BigInteger, nullable=False)
    giro = db.Column(db.Text, nullable=False)
    telefono = db.Column(db.Text, nullable=False)
    correo = db.Column(db.Text, nullable=False)
    codigo_postal = db.Column(db.Text, nullable=False)
    calle = db.Column(db.Text, nullable=False)
    no_exterior = db.Column(db.Text, nullable=False)
    no_interior = db.Column(db.Text, nullable=True)
    colonia = db.Column(db.Text, nullable=False)
    ciudad = db.Column(db.Text, nullable=False)
    estado = db.Column(db.Text, nullable=False)
    tiene_trabajadores = db.Column(db.Boolean, nullable=False, default=False)
    tipo_nomina = db.Column(db.Text, nullable=True)
    estatus = db.Column(db.Text, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "nombre_completo": self.nombre_completo,
            "rfc": self.rfc,
            "tipo_persona": self.tipo_persona,
            "estatus": self.estatus
        }