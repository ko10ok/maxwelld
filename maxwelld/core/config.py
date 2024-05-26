import os
from pathlib import Path


class Config:
    project: str = os.environ.get('COMPOSE_PROJECT_NAME')
    non_stop_containers: list[str] = os.environ.get('NON_STOP_CONTAINERS').split(',')
    tmp_envs_path: Path = Path(os.environ.get('TMP_ENVS_DIRECTORY'))
    compose_files_path: Path = Path(os.environ.get('COMPOSE_FILES_DIRECTORY'))
    in_docker_project_root_path: Path = Path(os.environ.get('PROJECT_ROOT_DIRECTORY'))
    env_file_name: str = os.environ.get('TMP_ENVS_REGISTER_FILE')
    env_file_path: Path = tmp_envs_path / env_file_name
    host_project_root_directory: Path = Path(os.environ.get('HOST_PROJECT_ROOT_DIRECTORY'))
    env_tmp_directory: Path = Path(os.environ.get('TMP_ENVS_DIRECTORY'))
    host_env_tmp_directory: Path = Path(os.environ.get(
        'HOST_TMP_ENV_DIRECTORY',
        host_project_root_directory / env_tmp_directory.name
    ))
