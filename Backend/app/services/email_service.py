"""Envío de correos. Por ahora síncrono; la arquitectura prevé moverlo a Celery (jobs/email_job)."""
from flask import current_app
from flask_mail import Message

from app.extensions import mail


def activation_url(token: str) -> str:
    return f"{current_app.config['FRONTEND_URL']}/activar-cuenta?token={token}"


def send_activation_email(user, token: str) -> bool:
    """Envía el enlace para definir contraseña. Devuelve False si no se pudo enviar.

    Un fallo de correo no debe deshacer el alta del colaborador: se registra y se informa.
    """
    cfg = current_app.config
    url = activation_url(token)

    if not cfg.get("MAIL_SERVER"):
        if cfg["ENV_NAME"] != "production":
            current_app.logger.warning("SMTP no configurado. Enlace de activación para %s: %s", user.correo_institucional, url)
        else:
            current_app.logger.error("SMTP no configurado: no se envió el enlace de activación a colaborador id=%s", user.id)
        return False

    hours = cfg["ACTIVATION_LINK_HOURS"]
    msg = Message(
        subject="Activa tu cuenta en SISCONNI",
        recipients=[user.correo_institucional],
        body=(
            f"Hola {user.nombre_completo},\n\n"
            "Se creó tu cuenta en SISCONNI, el sistema de gestión del despacho Téllez Ponce y Asociados.\n"
            f"Define tu contraseña con el siguiente enlace (vigente {hours} horas):\n\n"
            f"{url}\n\n"
            "Si no esperabas este correo, ignóralo."
        ),
    )
    try:
        mail.send(msg)
        return True
    except Exception:  # noqa: BLE001 - cualquier fallo SMTP se reporta, no se propaga
        current_app.logger.exception("Falló el envío del correo de activación (colaborador id=%s)", user.id)
        return False