import hashlib
import json
import uuid
from datetime import UTC, datetime
from typing import Any


def _default(value: Any) -> Any:
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, datetime):
        return value.astimezone(UTC).isoformat(timespec="microseconds")
    raise TypeError(f"tipe tidak dapat diserialisasi: {type(value).__name__}")


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=_default,
    )


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def content_hash(text: str) -> str:
    return sha256_hex(text)


def config_hash(value: Any) -> str:
    return sha256_hex(canonical_json(value))
