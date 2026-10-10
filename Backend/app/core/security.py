import hashlib
import secrets


def generate_token(nbytes: int = 32) -> tuple[str, str]:
    """Devuelve (token_en_claro, hash_sha256). Solo el hash se guarda en la base."""
    raw = secrets.token_urlsafe(nbytes)
    return raw, hash_token(raw)


def hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()