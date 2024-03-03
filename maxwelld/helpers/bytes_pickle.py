import base64
import pickle
from typing import Any


def base64_pickled(obj: Any) -> str:
    return base64.b64encode(pickle.dumps(obj)).decode('utf-8')


def debase64_pickled(data: str) -> Any:
    return pickle.loads(base64.b64decode(data))
