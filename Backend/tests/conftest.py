import os
import uuid

import pytest
from flask_jwt_extended import create_access_token
from sqlalchemy import text

from app import create_app
from app.config import _normalize_database_url
from app.extensions import db
from app.models.user import ESTATUS_ACTIVO, Colaborador


def _pg_url() -> str:
    url = os.getenv("TEST_DATABASE_URL", "").strip()
    return url if url.startswith(("postgres://", "postgresql")) else ""


@pytest.fixture(scope="session")
def pg_schema():
    """Crea (y al final elimina) un esquema aislado. None cuando se usa SQLite."""
    url = _pg_url()
    if not url:
        yield None
        return

    import psycopg2

    schema = f"test_{uuid.uuid4().hex[:10]}"
    sslmode = os.getenv("DB_SSLMODE", "require")
    conn = psycopg2.connect(url, sslmode=sslmode)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(f'CREATE SCHEMA "{schema}"')
    try:
        yield schema
    finally:
        with conn.cursor() as cur:
            cur.execute(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE')
        conn.close()


@pytest.fixture()
def app(pg_schema):
    overrides = {}
    if pg_schema:
        overrides = {
            "SQLALCHEMY_DATABASE_URI": _normalize_database_url(_pg_url()),
            "SQLALCHEMY_ENGINE_OPTIONS": {
                "pool_pre_ping": True,
                # search_path solo con el esquema de prueba: así no ve ni toca `public`.
                "connect_args": {
                    "sslmode": os.getenv("DB_SSLMODE", "require"),
                    "options": f"-csearch_path={pg_schema}",
                },
            },
        }

    app = create_app("testing", overrides)
    with app.app_context():
        db.create_all()  # en PostgreSQL solo crea lo que falte dentro del esquema de prueba
        if pg_schema:
            _truncate_all()
        yield app
        db.session.remove()
        if pg_schema:
            _truncate_all()
        else:
            db.drop_all()
        db.engine.dispose()


def _truncate_all() -> None:
    tables = ", ".join(f'"{t.name}"' for t in db.metadata.sorted_tables)
    db.session.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))
    db.session.commit()


@pytest.fixture()
def client(app):
    return app.test_client()


def _make_user(correo: str, rol: str, estatus: str = ESTATUS_ACTIVO) -> Colaborador:
    user = Colaborador(
        nombre_completo=f"Usuario {rol.title()}",
        correo_institucional=correo,
        rol=rol,
        grado_escalafon="ADMIN",
        estatus=estatus,
        telefono_despacho="4420000000",
        telefono_personal="4421111111",
        emergencia_nombre="Contacto Emergencia",
        emergencia_telefono="4422222222",
    )
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture()
def make_user(app):
    return _make_user


@pytest.fixture()
def auth_headers(app):
    def _headers(user: Colaborador) -> dict:
        return {"Authorization": f"Bearer {create_access_token(identity=str(user.id))}"}

    return _headers


@pytest.fixture()
def valid_payload() -> dict:
    return {
        "nombre_completo": "María Fernanda López Ruiz",
        "telefono_despacho": "2461234567",
        "correo_institucional": "maria.lopez@despacho.com",
        "rol": "CONTADOR",
        "grado_escalafon": "JUNIOR",
        "telefono_personal": "2469876543",
        "emergencia_nombre": "José López",
        "emergencia_telefono": "2465550101",
    }