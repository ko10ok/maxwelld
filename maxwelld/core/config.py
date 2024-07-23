import os
from pathlib import Path


class Config:
    def __init__(self):
        self.project: str = os.environ.get('COMPOSE_PROJECT_NAME')
        self.non_stop_containers: list[str] = os.environ.get('NON_STOP_CONTAINERS').split(',')
        self.tmp_envs_path: Path = Path(os.environ.get('TMP_ENVS_DIRECTORY'))
        self.compose_files_path: Path = Path(os.environ.get('COMPOSE_FILES_DIRECTORY'))
        self.in_docker_project_root_path: Path = Path(os.environ.get('PROJECT_ROOT_DIRECTORY'))
        self.env_file_name: str = os.environ.get('TMP_ENVS_REGISTER_FILE')
        self.env_file_path: Path = self.tmp_envs_path / self.env_file_name
        self.host_project_root_directory: Path = Path(os.environ.get('HOST_PROJECT_ROOT_DIRECTORY'))
        self.env_tmp_directory: Path = Path(os.environ.get('TMP_ENVS_DIRECTORY'))
        self.host_env_tmp_directory: Path = Path(os.environ.get(
            'HOST_TMP_ENV_DIRECTORY',
            self.host_project_root_directory / self.env_tmp_directory.name
        ))
        self.docker_host = os.environ.get('DOCKER_HOST')
        self.compose_project_name = os.environ.get('COMPOSE_PROJECT_NAME')
        self.default_compose_files: str = os.environ.get('DEFAULT_COMPOSE_FILES')
        assert self.default_compose_files != '', 'unset DEFAULT_COMPOSE_FILES'
        self.verbose_docker_compose_commands = bool(os.environ.get('VERBOSE_DOCKER_COMPOSE_OUTPUT_TO_STDOUT', False))
        self.verbose_docker_compose_ps_commands = bool(os.environ.get('VERBOSE_DOCKER_COMPOSE_PS_OUTPUT_TO_STDOUT', False))
        # TODO call it pre migration checks
        self.service_up_check_attempts = int(os.environ.get('PRE_MIGRATIONS_CHECK_SERVICE_UP_ATTEMPTS', 60))
        self.service_up_check_delay = int(os.environ.get('PRE_MIGRATIONS_CHECK_SERVICE_UP_CHECK_DELAY', 3))
