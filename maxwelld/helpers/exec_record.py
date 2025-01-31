from typing import NamedTuple


class ExecRecord(NamedTuple):
    env_id: str
    container: str
    log_file: str
