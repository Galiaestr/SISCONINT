from flask import Flask

from app.config import get_config
from app.core.errors import register_error_handlers, register_jwt_handlers
from app.core.security import init_token_blocklist
from app.extensions import cors, db, jwt, mail


def create_app(config_name: str | None = None, overrides: dict | None = None) -> Flask:
    app = Flask(__name__)
    app.config.from_object(get_config(config_name))
    if overrides:  # lo usan las pruebas para apuntar a un esquema de PostgreSQL aislado
        app.config.update(overrides)
    app.url_map.strict_slashes = False

    if app.config["ENV_NAME"] == "production" and not app.config["JWT_SECRET_KEY"]:
        raise RuntimeError("JWT_SECRET_KEY es obligatorio en producción")
    if not app.config["SQLALCHEMY_DATABASE_URI"]:
        raise RuntimeError("DATABASE_URL no está configurada (revisa tu archivo .env)")

    db.init_app(app)
    jwt.init_app(app)
    mail.init_app(app)
    init_token_blocklist(app)
    cors.init_app(
        app,
        resources={r"/api/*": {"origins": [app.config["FRONTEND_URL"]]}},
        supports_credentials=True,
    )

    from app import models  # noqa: F401  (registra los modelos en SQLAlchemy)
    from app.api import api_bp
    from app.cli import register_cli

    register_jwt_handlers()
    register_error_handlers(app)
    app.register_blueprint(api_bp)
    register_cli(app)

    @app.get("/health")
    def health():
        return {"status": "ok"}

    return app