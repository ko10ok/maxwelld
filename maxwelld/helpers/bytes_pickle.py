import base64
import pickle
from typing import Any


def base64_encode(data: bytes) -> str:
    """Кодирование в Base64 без знака ="""
    encoded = base64.urlsafe_b64encode(data).decode().rstrip("=")  # Удаляем =
    return encoded


def base64_decode(encoded: str) -> bytes:
    """Декодирование Base64 без знака = (добавляем = обратно)"""
    padding = len(encoded) % 4  # Определяем, сколько = нужно добавить
    encoded += "=" * (4 - padding) if padding else ""
    return base64.urlsafe_b64decode(encoded)


def base64_pickled(obj: Any) -> str:
    return base64_encode(pickle.dumps(obj))


def debase64_pickled(data: str) -> Any:
    return pickle.loads(base64_decode(data))
