"""RG-04: se guarda y compara en UTC; America/Mexico_City es solo de presentación."""
from datetime import datetime, timezone


def utcnow() -> datetime:
    return datetime.now(timezone.utc)