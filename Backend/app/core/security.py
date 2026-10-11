import hashlib
import secrets
from functools import lru_cache

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

_hasher = PasswordHasher()  # argon2id con parámetros recomendados


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