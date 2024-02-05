from typing import TypedDict

from maxwelld import Environment


class RequestType(TypedDict):
    name: str
    config_template: Environment
    compose_files: str
    isolation: bool
    parallelism_limit: int
