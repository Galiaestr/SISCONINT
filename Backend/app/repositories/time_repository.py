from sqlalchemy import select

from app.extensions import db
from app.models.time_entry import TemporizadorActivo


def get_active_for_user(colaborador_id: int) -> TemporizadorActivo | None:
    return db.session.execute(
        select(TemporizadorActivo).where(
            TemporizadorActivo.colaborador_id == colaborador_id,
            TemporizadorActivo.deleted_at.is_(None),
        )
    ).scalar_one_or_none()
