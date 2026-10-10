from sqlalchemy.dialects.postgresql import JSONB

from app.core.datetime_utils import utcnow
from app.extensions import db

# BIGINT identity en PostgreSQL; INTEGER en SQLite para que autoincremente en pruebas.
BigId = db.BigInteger().with_variant(db.Integer(), "sqlite")
JsonType = db.JSON().with_variant(JSONB(), "postgresql")


class TimestampMixin:
    """RG-13: created_at/updated_at. updated_at también lo mantiene un trigger en la base."""

    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)


class SoftDeleteMixin:
    """RG-03: eliminación lógica."""

    deleted_at = db.Column(db.DateTime(timezone=True))