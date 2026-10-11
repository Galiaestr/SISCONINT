"""Comandos de apoyo:  flask seed-owner | set-password | dev-token."""
import click
from flask import current_app
from flask_jwt_extended import create_access_token
from marshmallow import ValidationError
from sqlalchemy import func, select

from app.core import audit
from app.core.security import hash_password, password_policy_errors
from app.extensions import db
from app.models.user import ESTATUS_ACTIVO, ROL_DUENO, Colaborador
from app.schemas.user_schema import ColaboradorCreateSchema


def _find_user(correo: str) -> Colaborador | None:
    return db.session.execute(
        select(Colaborador).where(
            func.lower(Colaborador.correo_institucional) == correo.strip().lower(),
            Colaborador.deleted_at.is_(None),
        )
    ).scalar_one_or_none()


def register_cli(app):
    @app.cli.command("seed-owner")
    @click.option("--nombre", prompt="Nombre completo")
    @click.option("--correo", prompt="Correo institucional")
    @click.option("--telefono-despacho", prompt="Teléfono del despacho (10 dígitos)")
    @click.option("--telefono-personal", prompt="Teléfono personal (10 dígitos)")
    @click.option("--emergencia-nombre", prompt="Nombre del contacto de emergencia")
    @click.option("--emergencia-telefono", prompt="Teléfono de emergencia (10 dígitos)")
    def seed_owner(nombre, correo, telefono_despacho, telefono_personal, emergencia_nombre, emergencia_telefono):
        """Crea el primer usuario Dueño (sin contraseña: usa después `flask set-password`)."""
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

        if _find_user(data["correo_institucional"]):
            raise click.ClickException("Ya existe un colaborador con ese correo")

        owner = Colaborador(**data, estatus=ESTATUS_ACTIVO)
        db.session.add(owner)
        db.session.flush()
        audit.log(None, "colaborador", owner.id, audit.CREAR, {"origen": "seed-owner", "rol": ROL_DUENO})
        db.session.commit()
        click.echo(f"Dueño creado (id={owner.id}). Define su contraseña con: flask --app wsgi set-password")

    @app.cli.command("set-password")
    @click.option("--correo", prompt="Correo del colaborador")
    @click.password_option("--password", prompt="Nueva contraseña", confirmation_prompt=True)
    def set_password(correo, password):
        """Define la contraseña (hash argon2) de un colaborador. Cumple la política RG-05."""
        user = _find_user(correo)
        if user is None:
            raise click.ClickException("Colaborador no encontrado")

        problems = password_policy_errors(password, user.correo_institucional)
        if problems:
            raise click.ClickException("Contraseña no válida: " + "; ".join(problems))

        user.password_hash = hash_password(password)
        audit.log(None, "colaborador", user.id, audit.MODIFICAR, {"campo": "password", "origen": "set-password"})
        db.session.commit()
        click.echo(f"Contraseña actualizada para {user.correo_institucional}.")

    @app.cli.command("dev-token")
    @click.option("--correo", required=True)
    def dev_token(correo):
        """Imprime un JWT de acceso para probar con la cabecera Authorization (sin cookies)."""
        if current_app.config["ENV_NAME"] == "production":
            raise click.ClickException("Deshabilitado en producción")
        user = _find_user(correo)
        if user is None or not user.activo:
            raise click.ClickException("Colaborador no encontrado o inactivo")
        click.echo(create_access_token(identity=str(user.id)))
