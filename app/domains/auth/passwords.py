import base64
import hashlib
import hmac
import os


PASSWORD_HASH_SCHEME = "scrypt"
PASSWORD_HASH_N = 2**14
PASSWORD_HASH_R = 8
PASSWORD_HASH_P = 1
PASSWORD_HASH_DKLEN = 64
UNUSABLE_PASSWORD_HASH = "!"


def normalize_email(email: str) -> str:
    return email.strip().lower()


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    derived_key = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=PASSWORD_HASH_N,
        r=PASSWORD_HASH_R,
        p=PASSWORD_HASH_P,
        dklen=PASSWORD_HASH_DKLEN,
    )
    encoded_salt = base64.b64encode(salt).decode("ascii")
    encoded_key = base64.b64encode(derived_key).decode("ascii")
    return f"{PASSWORD_HASH_SCHEME}${PASSWORD_HASH_N}${PASSWORD_HASH_R}${PASSWORD_HASH_P}${encoded_salt}${encoded_key}"


def verify_password(password: str, password_hash: str) -> bool:
    if not has_usable_password(password_hash):
        return False
    try:
        scheme, n_value, r_value, p_value, encoded_salt, encoded_key = password_hash.split("$", maxsplit=5)
    except ValueError:
        return False
    if scheme != PASSWORD_HASH_SCHEME:
        return False
    try:
        expected_key = base64.b64decode(encoded_key.encode("ascii"))
        derived_key = hashlib.scrypt(
            password.encode("utf-8"),
            salt=base64.b64decode(encoded_salt.encode("ascii")),
            n=int(n_value),
            r=int(r_value),
            p=int(p_value),
            dklen=len(expected_key),
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(derived_key, expected_key)


def make_unusable_password_hash() -> str:
    return UNUSABLE_PASSWORD_HASH


def has_usable_password(password_hash: str | None) -> bool:
    return bool(password_hash and password_hash != UNUSABLE_PASSWORD_HASH)
