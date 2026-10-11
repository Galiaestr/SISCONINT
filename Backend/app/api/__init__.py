from flask import Blueprint

from app.api import auth, users

api_bp = Blueprint("api", __name__, url_prefix="/api/v1")
api_bp.register_blueprint(auth.bp)
api_bp.register_blueprint(users.bp)
