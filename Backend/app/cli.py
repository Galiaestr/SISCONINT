"""Comandos de apoyo:  flask seed-owner  |  flask dev-token."""
import click
from flask import current_app
from flask_jwt_extended import create_access_token
from marshmallow import ValidationError
from sqlalchemy import func, select

from app.core import audit
from app.extensions import db
from app.models.user import ESTATUS_ACTIVO, ROL_DUENO, Colaborador
from app.schemas.user_schema import ColaboradorCreateSchema


def register_cli(app):
    @app.cli.command("seed-owner")
    @click.option("--nombre", prompt="Nombre completo")
    @click.option("--correo", prompt="Correo institucional")
    @click.option("--telefono-despacho", prompt="Teléfono del despacho (10 dígitos)")
    @click.option("--telefono-personal", prompt="Teléfono personal (10 dígitos)")
    @click.option("--emergencia-nombre", prompt="Nombre del contacto de emergencia")
    @click.option("--emergencia-telefono", prompt="Teléfono de emergencia (10 dígitos)")
    def seed_owner(nombre, correo, telefono_despacho, telefono_personal, emergencia_nombre, emergencia_telefono):
        """Crea el primer usuario Dueño (sin contraseña; el login llega con HU_01)."""
        try:
            data = ColaboradorCreateSchema().load(
                {
                    "nombre_completo": nombre,
                    "correo_institucional": correo,
                    "telefono_despacho": telefono_despacho,
                    "telefono_personal": telefono_personal,
                    "emergencia_nombre": emergencia_nombre,
                    "emergencia_telefono": emergencia_telefono,
                    "rol": ROL_DUENO,
                    "grado_escalafon": "ADMIN",
                }
            )
        except ValidationError as err:
            raise click.ClickException(f"Datos no válidos: {err.messages}")

        exists = db.session.execute(
            select(Colaborador.id).where(func.lower(Colaborador.correo_institucional) == data["correo_institucional"])
        ).first()
        if exists:
            raise click.ClickException("Ya existe un colaborador con ese correo")

        owner = Colaborador(**data, estatus=ESTATUS_ACTIVO)
        db.session.add(owner)
        db.session.flush()
        audit.log(None, "colaborador", owner.id, audit.CREAR, {"origen": "seed-owner", "rol": ROL_DUENO})
        db.session.commit()
        click.echo(f"Dueño creado (id={owner.id}).")

    @app.cli.command("dev-token")
    @click.option("--correo", required=True)
    def dev_token(correo):
        """Imprime un JWT de acceso (30 min) para probar la API mientras no exista el login."""
        if current_app.config["ENV_NAME"] == "production":
            raise click.ClickException("Deshabilitado en producción")
        user = db.session.execute(
            select(Colaborador).where(func.lower(Colaborador.correo_institucional) == correo.lower())
        ).scalar_one_or_none()
        if user is None or not user.activo:
            raise click.ClickException("Colaborador no encontrado o inactivo")
        click.echo(create_access_token(identity=str(user.id)))