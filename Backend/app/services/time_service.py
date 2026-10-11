"""Consultas de tiempo usadas por otros módulos. El alta/parada del timer es HU de temporizador."""
from app.models.time_entry import TemporizadorActivo
from app.repositories import time_repository


def get_active_timer(colaborador_id: int) -> TemporizadorActivo | None:
    return time_repository.get_active_for_user(colaborador_id)
