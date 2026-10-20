import base64
import hashlib
import hmac
import secrets

SCRYPT_N = 2**14
SCRYPT_R = 8
SCRYPT_P = 1
SCRYPT_DKLEN = 32
SALT_BYTES = 16
MIN_PASSWORD_LENGTH = 12
SCHEME = "scrypt"


def _b64(raw: bytes) -> str:
    return base64.b64encode(raw).decode("ascii")


def _unb64(value: str) -> bytes:
    return base64.b64decode(value.encode("ascii"))


def _derive(password: str, salt: bytes, n: int, r: int, p: int, dklen: int) -> bytes:
    return hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=n,
        r=r,
        p=p,
        dklen=dklen,
        maxmem=128 * n * r * 2,
    )


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(SALT_BYTES)
    digest = _derive(password, salt, SCRYPT_N, SCRYPT_R, SCRYPT_P, SCRYPT_DKLEN)
    return f"{SCHEME}${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}${_b64(salt)}${_b64(digest)}"


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, n, r, p, salt_b64, digest_b64 = stored.split("$")
        if scheme != SCHEME:
            return False
        expected = _unb64(digest_b64)
        actual = _derive(password, _unb64(salt_b64), int(n), int(r), int(p), len(expected))
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(actual, expected)


DUMMY_PASSWORD_HASH = hash_password(secrets.token_urlsafe(24))


def password_policy_violation(password: str) -> str | None:
    if len(password) < MIN_PASSWORD_LENGTH:
        return f"Kata sandi minimal {MIN_PASSWORD_LENGTH} karakter"
    if password.strip() != password:
        return "Kata sandi tidak boleh diawali atau diakhiri spasi"
    if len(set(password)) < 5:
        return "Kata sandi terlalu sederhana"
    return None


def new_session_token() -> str:
    return secrets.token_urlsafe(32)


def hash_session_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
