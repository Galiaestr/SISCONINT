"""HU_05: Registrar colaborador."""
import hashlib
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.extensions import db, mail
from app.models.audit_log import BitacoraAuditoria
from app.models.auth_token import EnlaceActivacion
from app.models.user import Colaborador

URL = "/api/v1/users"

REQUIRED = {
    "nombre_completo", "telefono_despacho", "correo_institucional", "rol",
    "grado_escalafon", "telefono_personal", "emergencia_nombre", "emergencia_telefono",
}


@pytest.fixture()
def owner(make_user):
    return make_user("dueno@despacho.com", "DUENO")


@pytest.fixture()
def admin(make_user):
    return make_user("admin@despacho.com", "ADMINISTRADOR")


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


# ---------------------------------------------------------------- éxito
def test_owner_registers_collaborator(client, auth_headers, owner, valid_payload):
    res = client.post(URL, json=valid_payload, headers=auth_headers(owner))
    assert res.status_code == 201
    data = res.get_json()["data"]
    assert data["estatus"] == "ACTIVO"
    assert data["correo_institucional"] == "maria.lopez@despacho.com"
    assert data["rol"] == "CONTADOR"
    assert "password_hash" not in data
    assert data["correo_activacion_enviado"] is True

    created = db.session.get(Colaborador, data["id"])
    assert created.password_hash is None
    assert created.created_by == owner.id


def test_activation_link_is_stored_hashed_with_48h_expiry_and_emailed(client, auth_headers, owner, valid_payload):
    with mail.record_messages() as outbox:
        res = client.post(URL, json=valid_payload, headers=auth_headers(owner))
    assert res.status_code == 201

    assert len(outbox) == 1
    assert outbox[0].recipients == ["maria.lopez@despacho.com"]
    token = outbox[0].body.split("token=")[1].split()[0]

    link = db.session.execute(select(EnlaceActivacion)).scalar_one()
    assert link.token_hash == hashlib.sha256(token.encode()).hexdigest()
    assert token not in link.token_hash  # el token en claro no se guarda
    remaining = _aware(link.vence_en) - datetime.now(timezone.utc)
    assert timedelta(hours=47, minutes=55) < remaining <= timedelta(hours=48)


def test_registration_is_audited(client, auth_headers, owner, valid_payload):
    res = client.post(URL, json=valid_payload, headers=auth_headers(owner))
    entry = db.session.execute(select(BitacoraAuditoria)).scalar_one()
    assert (entry.usuario_id, entry.entidad, entry.entidad_id, entry.accion) == (
        owner.id, "colaborador", res.get_json()["data"]["id"], "CREAR",
    )


def test_optional_fields_are_saved(client, auth_headers, owner, valid_payload):
    valid_payload.update(
        licenciatura="Contaduría Pública", cedula="1234567", calle="Av. Juárez",
        no_ext_int="12 / 3", colonia="Centro", municipio="Tlaxcala", estado="Tlaxcala",
    )
    res = client.post(URL, json=valid_payload, headers=auth_headers(owner))
    assert res.status_code == 201
    data = res.get_json()["data"]
    assert data["cedula"] == "1234567" and data["municipio"] == "Tlaxcala"


def test_empty_optional_strings_become_null_and_enums_are_case_insensitive(client, auth_headers, owner, valid_payload):
    valid_payload.update(cedula="", licenciatura="  ", rol="contador", grado_escalafon="senior")
    res = client.post(URL, json=valid_payload, headers=auth_headers(owner))
    assert res.status_code == 201
    data = res.get_json()["data"]
    assert data["cedula"] is None and data["licenciatura"] is None
    assert data["rol"] == "CONTADOR" and data["grado_escalafon"] == "SENIOR"


def test_email_failure_does_not_undo_registration(client, auth_headers, owner, valid_payload, monkeypatch):
    def boom(_msg):
        raise ConnectionError("smtp caído")

    monkeypatch.setattr(mail, "send", boom)
    res = client.post(URL, json=valid_payload, headers=auth_headers(owner))
    assert res.status_code == 201
    assert res.get_json()["data"]["correo_activacion_enviado"] is False
    assert db.session.execute(select(Colaborador).where(Colaborador.rol == "CONTADOR")).first() is not None


# ---------------------------------------------------------------- roles asignables
@pytest.mark.parametrize("rol", ["DUENO", "ADMINISTRADOR", "COORDINADOR", "CONTADOR"])
def test_owner_can_assign_any_role(client, auth_headers, owner, valid_payload, rol):
    valid_payload["rol"] = rol
    assert client.post(URL, json=valid_payload, headers=auth_headers(owner)).status_code == 201


@pytest.mark.parametrize("rol", ["COORDINADOR", "CONTADOR"])
def test_admin_can_assign_coordinator_or_accountant(client, auth_headers, admin, valid_payload, rol):
    valid_payload["rol"] = rol
    assert client.post(URL, json=valid_payload, headers=auth_headers(admin)).status_code == 201


@pytest.mark.parametrize("rol", ["DUENO", "ADMINISTRADOR"])
def test_admin_cannot_assign_owner_or_admin(client, auth_headers, admin, valid_payload, rol):
    valid_payload["rol"] = rol
    res = client.post(URL, json=valid_payload, headers=auth_headers(admin))
    assert res.status_code == 403
    assert db.session.execute(select(Colaborador).where(Colaborador.rol == rol)).first() is None


# ---------------------------------------------------------------- permisos (RG-02)
@pytest.mark.parametrize("rol", ["COORDINADOR", "CONTADOR"])
def test_coordinator_and_accountant_are_denied(client, auth_headers, make_user, valid_payload, rol):
    actor = make_user(f"{rol.lower()}@despacho.com", rol)
    res = client.post(URL, json=valid_payload, headers=auth_headers(actor))
    assert res.status_code == 403
    assert res.get_json()["error"]["message"] == "No tienes permiso para esta acción"


def test_forbidden_does_not_leak_validation_details(client, auth_headers, make_user):
    actor = make_user("contador@despacho.com", "CONTADOR")
    res = client.post(URL, json={}, headers=auth_headers(actor))
    assert res.status_code == 403
    assert "fields" not in res.get_json()["error"]


def test_requires_authentication(client, valid_payload):
    assert client.post(URL, json=valid_payload).status_code == 401


def test_inactive_actor_is_rejected(client, auth_headers, make_user, valid_payload):
    inactive_owner = make_user("viejo@despacho.com", "DUENO", estatus="INACTIVO")
    assert client.post(URL, json=valid_payload, headers=auth_headers(inactive_owner)).status_code == 401


# ---------------------------------------------------------------- validaciones (RG-09 / RG-10)
def test_all_required_fields_are_reported(client, auth_headers, owner):
    res = client.post(URL, json={}, headers=auth_headers(owner))
    assert res.status_code == 422
    fields = res.get_json()["error"]["fields"]
    assert set(fields) == REQUIRED
    assert all(msgs == ["Campo obligatorio"] for msgs in fields.values())


@pytest.mark.parametrize("field", sorted(REQUIRED))
def test_each_required_field_rejects_blank(client, auth_headers, owner, valid_payload, field):
    valid_payload[field] = "   "
    res = client.post(URL, json=valid_payload, headers=auth_headers(owner))
    assert res.status_code == 422
    assert res.get_json()["error"]["fields"][field] == ["Campo obligatorio"]


@pytest.mark.parametrize(
    "field,value",
    [
        ("correo_institucional", "no-es-correo"),
        ("correo_institucional", "a@b"),
        ("telefono_despacho", "123456789"),      # 9 dígitos
        ("telefono_personal", "12345678901"),    # 11 dígitos
        ("emergencia_telefono", "55-1234-5678"),
        ("cedula", "123456"),                    # 6 dígitos
        ("cedula", "123456789"),                 # 9 dígitos
        ("cedula", "12A4567"),
        ("rol", "SUPERUSUARIO"),
        ("grado_escalafon", "MASTER"),
    ],
)
def test_invalid_formats_are_rejected(client, auth_headers, owner, valid_payload, field, value):
    valid_payload[field] = value
    res = client.post(URL, json=valid_payload, headers=auth_headers(owner))
    assert res.status_code == 422
    assert field in res.get_json()["error"]["fields"]
    assert db.session.execute(select(Colaborador).where(Colaborador.id != owner.id)).first() is None


def test_body_must_be_a_json_object(client, auth_headers, owner):
    res = client.post(URL, data="no es json", headers=auth_headers(owner))
    assert res.status_code == 422


# ---------------------------------------------------------------- correo único
def test_duplicate_email_is_rejected_case_insensitively(client, auth_headers, owner, valid_payload):
    assert client.post(URL, json=valid_payload, headers=auth_headers(owner)).status_code == 201
    valid_payload["correo_institucional"] = "MARIA.LOPEZ@Despacho.com"
    res = client.post(URL, json=valid_payload, headers=auth_headers(owner))
    assert res.status_code == 409
    err = res.get_json()["error"]
    assert err["message"] == "El correo ya está registrado"
    assert err["fields"]["correo_institucional"] == ["El correo ya está registrado"]
    assert db.session.execute(select(Colaborador).where(Colaborador.rol == "CONTADOR")).scalars().all().__len__() == 1


def test_email_of_existing_owner_cannot_be_reused(client, auth_headers, owner, valid_payload):
    valid_payload["correo_institucional"] = owner.correo_institucional
    assert client.post(URL, json=valid_payload, headers=auth_headers(owner)).status_code == 409