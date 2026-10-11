"""HU_04: Cerrar sesión. El token se invalida en servidor; un temporizador activo lo impide."""
from flask_jwt_extended import decode_token

from app.core.datetime_utils import utcnow
from app.core.security import hash_password
from app.extensions import db
from app.models.time_entry import TemporizadorActivo
from app.models.user import Colaborador

LOGOUT = "/api/v1/auth/logout"
ME = "/api/v1/auth/me"
LOGIN = "/api/v1/auth/login"
REFRESH = "/api/v1/auth/refresh"
PASSWORD = "Password1!"


def _user_with_password(make_user, correo="contador@despacho.com") -> Colaborador:
    user = make_user(correo, "CONTADOR")
    user.password_hash = hash_password(PASSWORD)
    db.session.commit()
    return user


def _csrf(client, name: str = "csrf_access_token") -> dict:
    cookie = client.get_cookie(name)
    assert cookie is not None
    return {"X-CSRF-TOKEN": cookie.value}


def _login(client, correo: str):
    return client.post(
        LOGIN,
        json={"correo_institucional": correo, "password": PASSWORD},
    )


def _start_timer(user: Colaborador) -> TemporizadorActivo:
    timer = TemporizadorActivo(colaborador_id=user.id, tarea_id=1, iniciado_en=utcnow())
    db.session.add(timer)
    db.session.commit()
    return timer


def test_logout_requires_authentication(client):
    res = client.post(LOGOUT)
    assert res.status_code == 401
    assert res.get_json()["error"]["code"] == "UNAUTHORIZED"


def test_logout_with_bearer_token_invalidates_it_immediately(client, auth_headers, make_user):
    user = _user_with_password(make_user)
    headers = auth_headers(user)

    assert client.get(ME, headers=headers).status_code == 200
    res = client.post(LOGOUT, headers=headers)
    assert res.status_code == 200
    assert res.get_json()["data"]["message"] == "Sesión cerrada correctamente"

    blocked = client.get(ME, headers=headers)
    assert blocked.status_code == 401
    assert blocked.get_json()["error"]["code"] == "UNAUTHORIZED"


def test_logout_clears_cookies_and_blocks_browser_back_via_me(client, make_user):
    user = _user_with_password(make_user)
    login = _login(client, user.correo_institucional)
    assert login.status_code == 200
    assert client.get(ME).status_code == 200

    access_before = client.get_cookie("SISCONNI_access_token").value
    res = client.post(LOGOUT, headers=_csrf(client))
    assert res.status_code == 200
    assert client.get(ME).status_code == 401

    # Simula el botón Atrás: el navegador reenvía el JWT que ya fue invalidado.
    client.set_cookie("SISCONNI_access_token", access_before)
    me = client.get(ME)
    assert me.status_code == 401
    assert me.get_json()["error"]["code"] == "UNAUTHORIZED"


def test_refresh_token_is_revoked_together_with_access(client, make_user):
    user = _user_with_password(make_user)
    assert _login(client, user.correo_institucional).status_code == 200

    access_cookie = client.get_cookie("SISCONNI_access_token")
    refresh_cookie = client.get_cookie("SISCONNI_refresh_token")
    csrf_refresh = client.get_cookie("csrf_refresh_token")
    assert access_cookie and refresh_cookie and csrf_refresh
    assert decode_token(access_cookie.value)["jti"]
    assert decode_token(refresh_cookie.value)["jti"]

    assert client.post(LOGOUT, headers=_csrf(client)).status_code == 200

    client.set_cookie("SISCONNI_access_token", access_cookie.value)
    client.set_cookie("SISCONNI_refresh_token", refresh_cookie.value, path="/api/v1/auth")
    client.set_cookie("csrf_refresh_token", csrf_refresh.value, path="/api/v1/auth")

    assert client.get(ME).status_code == 401
    res_refresh = client.post(REFRESH, headers={"X-CSRF-TOKEN": csrf_refresh.value})
    assert res_refresh.status_code == 401


def test_active_timer_blocks_logout_and_keeps_session(client, auth_headers, make_user):
    user = _user_with_password(make_user)
    _start_timer(user)
    headers = auth_headers(user)

    res = client.post(LOGOUT, headers=headers)
    assert res.status_code == 409
    err = res.get_json()["error"]
    assert err["code"] == "TIMER_ACTIVE"
    assert "temporizador activo" in err["message"].lower()

    assert client.get(ME, headers=headers).status_code == 200


def test_logout_succeeds_after_timer_is_stopped(client, auth_headers, make_user):
    user = _user_with_password(make_user)
    timer = _start_timer(user)
    headers = auth_headers(user)

    assert client.post(LOGOUT, headers=headers).status_code == 409

    timer.deleted_at = utcnow()
    db.session.commit()

    res = client.post(LOGOUT, headers=headers)
    assert res.status_code == 200
    assert client.get(ME, headers=headers).status_code == 401


def test_logout_does_not_revoke_another_users_session(client, auth_headers, make_user):
    alice = _user_with_password(make_user, "alice@despacho.com")
    bob = _user_with_password(make_user, "bob@despacho.com")
    alice_headers = auth_headers(alice)
    bob_headers = auth_headers(bob)

    assert client.post(LOGOUT, headers=alice_headers).status_code == 200
    assert client.get(ME, headers=alice_headers).status_code == 401
    assert client.get(ME, headers=bob_headers).status_code == 200
