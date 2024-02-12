from pathlib import Path
from typing import NamedTuple
from typing import Union

from maxwelld.env_description.env_types import Environment

EMPTY_ID = 'no_id'


class ComposeConfig(NamedTuple):
    compose_files: str
    parallel_env_limit: Union[int, None] = None


class EnvConfigInstance(NamedTuple):
    env_source: Environment
    env_id: str
    env_services_map: dict[str, str]
    env: Environment


class EnvConfigComposeInstance(NamedTuple):
    env_config_instance: EnvConfigInstance
    compose_files_source: str
    directory: Path
    compose_files: str


class InFlightEnv(NamedTuple):
    name: str
    id: str
    env: Environment
    envs_template: Environment
    compose_files_instance: EnvConfigComposeInstance
    params_hash: str = None
