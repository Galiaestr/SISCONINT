import hashlib
import secrets
import time
from functools import lru_cache

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from flask import current_app

_hasher = PasswordHasher()  # argon2id con parámetros recomendados


# ---------------------------------------------------------------- lista de jti revocados (HU_04)
class _MemoryBlocklist:
    """Reserva para pruebas y entornos sin Redis. TTL igual que en Redis."""

    def __init__(self):
        self._store: dict[str, float] = {}

    def add(self, jti: str, ttl: int) -> None:
        self._store[jti] = time.time() + max(1, ttl)

    def contains(self, jti: str) -> bool:
        expires_at = self._store.get(jti)
        if expires_at is None:
            return False
        if expires_at < time.time():
            del self._store[jti]
            return False
        return True


class _RedisBlocklist:
    """Arquitectura 3.4: jti revocados en Redis (logout, cambio de rol, etc.)."""

    def __init__(self, url: str):
        import redis

        self._redis = redis.Redis.from_url(url, decode_responses=True)

    def add(self, jti: str, ttl: int) -> None:
        self._redis.set(f"jwt:revoked:{jti}", "1", ex=max(1, ttl))

    def contains(self, jti: str) -> bool:
        return self._redis.get(f"jwt:revoked:{jti}") is not None


def init_token_blocklist(app) -> None:
    url = (app.config.get("REDIS_URL") or "").strip()
    if app.config.get("TESTING") or not url:
        app.extensions["token_blocklist"] = _MemoryBlocklist()
    else:
        app.extensions["token_blocklist"] = _RedisBlocklist(url)


def revoke_jti(jti: str, ttl_seconds: int) -> None:
    if not jti:
        return
    current_app.extensions["token_blocklist"].add(jti, ttl_seconds)


def jti_is_revoked(jti: str) -> bool:
    if not jti:
        return False
    store = current_app.extensions.get("token_blocklist")
    return bool(store and store.contains(jti))


# ---------------------------------------------------------------- tokens de un solo uso
def generate_token(nbytes: int = 32) -> tuple[str, str]:
    """Devuelve (token_en_claro, hash_sha256). Solo el hash se guarda en la base."""
    raw = secrets.token_urlsafe(nbytes)
    return raw, hash_token(raw)


def hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------- contraseñas
def hash_password(password: str) -> str:
    return _hasher.hash(password)


@lru_cache(maxsize=1)
def _dummy_hash() -> str:
    return _hasher.hash("hash-ficticio-para-igualar-tiempos")


def verify_password(stored_hash: str | None, password: str) -> bool:
    """True si la contraseña coincide. Nunca lanza.

    Si no hay hash (correo inexistente o cuenta sin contraseña) verifica contra uno ficticio:
    así el tiempo de respuesta no revela qué correos existen.
    """
    if not stored_hash:
        try:
            _hasher.verify(_dummy_hash(), password)
        except (VerificationError, InvalidHashError):
            pass
        return False
    try:
        return _hasher.verify(stored_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def password_policy_errors(password: str, correo: str | None = None) -> list[str]:
    """RG-05: mínimo 10 caracteres, mayúscula, minúscula, número y símbolo; distinta del correo."""
    errors: list[str] = []
    if len(password) < 10:
        errors.append("Mínimo 10 caracteres")
    if not any(c.isupper() for c in password):
        errors.append("Debe incluir una mayúscula")
    if not any(c.islower() for c in password):
        errors.append("Debe incluir una minúscula")
    if not any(c.isdigit() for c in password):
        errors.append("Debe incluir un número")
    if not any(not c.isalnum() and not c.isspace() for c in password):
        errors.append("Debe incluir un símbolo")
    if correo and password.strip().lower() == correo.strip().lower():
        errors.append("No puede ser igual al correo")
    return errors