import json
import os
import shutil
from copy import deepcopy
from pathlib import Path
from typing import Union

from rich.text import Text

from maxwelld.client.types import EnvironmentId
from maxwelld.core.docker_compose_interface import ServicesComposeState
from maxwelld.core.docker_compose_interface import dc_state
from maxwelld.core.exec_types import EMPTY_ID
from maxwelld.core.exec_types import EnvConfigInstance
from maxwelld.core.utils import actualize_in_flight
from maxwelld.core.utils import down_in_flight_envs
from maxwelld.core.utils import get_new_env_id
from maxwelld.core.utils import make_debug_bash_env
from maxwelld.core.utils import make_env_compose_instance_files
from maxwelld.core.utils import make_env_config_instance
from maxwelld.core.utils import run_env
from maxwelld.core.utils import unpack_services_env_template_params
from maxwelld.env_description.env_types import Environment
from maxwelld.helpers.bytes_pickle import base64_pickled
from maxwelld.helpers.bytes_pickle import debase64_pickled
from maxwelld.output.console import CONSOLE
from maxwelld.output.styles import Style


class MaxwellDemonService:
    def __init__(self, project: str, non_stop_containers: list[str]):
        assert shutil.which("docker"), 'Docker not installed'
        assert shutil.which("docker-compose"), 'Docker-compose not installed'
        assert os.environ.get('COMPOSE_FILES_DIRECTORY'), \
            'COMPOSE_FILES_DIRECTORY env should be set'
        assert os.environ.get('PROJECT_ROOT_DIRECTORY'), \
            'PROJECT_ROOT_DIRECTORY env should be set'
        assert os.environ.get('HOST_PROJECT_ROOT_DIRECTORY'), \
            'HOST_PROJECT_ROOT_DIRECTORY env should be set'
        assert os.environ.get('HOST_TMP_ENV_DIRECTORY'), \
            'HOST_TMP_ENV_DIRECTORY env should be set'

        self._project = project
        self._non_stop_containers = non_stop_containers
        self.tmp_envs_path = Path('/env-tmp')  # TODO get from envs
        self.compose_files_path = Path(os.environ.get('COMPOSE_FILES_DIRECTORY'))
        # self.dot_env_files_path = Path('/compose-files/envs')
        self.in_docker_project_root_path = Path(os.environ.get('PROJECT_ROOT_DIRECTORY'))
        self.env_file_name = 'envs.json'
        self.env_file_path = self.tmp_envs_path / self.env_file_name
        self.host_project_root_directory = Path(os.environ.get('HOST_PROJECT_ROOT_DIRECTORY'))
        self.host_env_tmp_directory = \
            self.host_project_root_directory / os.environ.get('HOST_TMP_ENV_DIRECTORY')
        self._started_envs: dict[str, dict] = actualize_in_flight(
            self.tmp_envs_path,
            self.env_file_name
        )

    def update_inflight_envs(self, name, config_template: Environment, compose_files: str, env_id: str):
        self._started_envs[name] = {
            'env_id': env_id,
            'params': {
                'name': name,
                'compose_files': compose_files,
                'config_template': base64_pickled(config_template)
            }
        }
        with open(self.env_file_path, 'w') as envs_file:
            envs_file.write(
                json.dumps(self._started_envs)
            )  # TODO fix sync when env upped but no record or record exists but bo env

    def get_existing_inflight_env(self, name: str, config_template: Environment,
                                  compose_files: str) -> Union[EnvConfigInstance, None]:
        if name in self._started_envs:
            env_id = self._started_envs[name]['env_id']
            env_config_instance = make_env_config_instance(
                env_template=config_template,
                env_id=env_id
            )

            # TODO run dc to check if services started, kill remainig if not.
            # compose_files_instance = make_env_compose_instance_files(
            #     env_config_instance,
            #     compose_files,
            #     project_network_name=self._project,
            #     host_project_root_directory=self.host_project_root_directory,
            #     compose_files_path=self.compose_files_path,
            #     dot_env_files_path=self.dot_env_files_path,
            #     tmp_env_path=self.tmp_envs_path,
            # )
            # make_debug_bash_env(compose_files_instance, self.host_env_tmp_directory)
            #
            return env_config_instance

        return None

    def get_existing_inflight_env_by_id(self, env_id: EnvironmentId) -> Union[EnvConfigInstance, None]:
        for env_name in self._started_envs:
            if self._started_envs[env_name]['env_id'] == env_id:
                config_template = debase64_pickled(self._started_envs[env_name]['params']['config_template'])
                env_config_instance = make_env_config_instance(
                    env_template=config_template,
                    env_id=env_id
                )
                return env_config_instance
        return None

    def check_one_env_limits(self):
        in_flight = deepcopy(self._started_envs)
        for env_name, env_params in in_flight.items():
            if env_params['env_id'] == EMPTY_ID:  # different env starts EMPTY_ID
                down_in_flight_envs(
                    self.tmp_envs_path,
                    EMPTY_ID,
                    self.in_docker_project_root_path,
                    except_containers=self._non_stop_containers
                )
                del self._started_envs[env_name]

    def up_compose(self, name: str, config_template: Environment, compose_files: str,
                   isolation=None, parallelism_limit=None, verbose=False) -> tuple[EnvironmentId, bool]:

        if existing_inflight_env := self.get_existing_inflight_env(
            name, config_template, compose_files
        ):
            if verbose:
                CONSOLE.print(f'Existing env for {name}: {self._started_envs[name]},'
                              f' no need to start again')
                CONSOLE.print(f'Config params:'
                              f' {unpack_services_env_template_params(existing_inflight_env.env)}')
                CONSOLE.print(f'Docker-compose access: '
                              f'> source ./env-tmp/{existing_inflight_env.env_id}/.env')
            return existing_inflight_env.env_id, False

        CONSOLE.print(
            Text('Starting new environment: ', style=Style.info)
            .append(Text(name, style=Style.mark))
        )
        new_env_id = get_new_env_id()
        if parallelism_limit == 1:
            CONSOLE.print(f'Using default service names with {parallelism_limit=}')
            new_env_id = EMPTY_ID
            self.check_one_env_limits()
        # TODO limit to parallelism_limit via while len(self._started_envs)

        env_config_instance = make_env_config_instance(
            env_template=config_template,
            env_id=new_env_id
        )

        compose_files_instance = make_env_compose_instance_files(
            env_config_instance,
            compose_files,
            project_network_name=self._project,
            host_project_root_directory=self.host_project_root_directory,
            compose_files_path=self.compose_files_path,
            # dot_env_files_path=self.dot_env_files_path,
            tmp_env_path=self.tmp_envs_path,
        )

        make_debug_bash_env(compose_files_instance, self.host_env_tmp_directory)
        CONSOLE.print(f'Docker-compose access: > source ./env-tmp/{new_env_id}/.env')

        # TODO uncomment
        in_flight_env = run_env(
            compose_files_instance, self.in_docker_project_root_path, self._non_stop_containers
        )

        # TODO should be transactional with file
        CONSOLE.print(Text(f'New environment for {name} started'))
        if verbose:
            CONSOLE.print(f'Config params: {unpack_services_env_template_params(env_config_instance.env)}')
        CONSOLE.print(
            Text(f'Docker-compose access: > ', style=Style.info)
            .append(Text(f'source ./env-tmp/{new_env_id}/.env', style=Style.mark_neutral))
        )

        self.update_inflight_envs(
            name,
            config_template=config_template,
            compose_files=compose_files_instance.compose_files,
            env_id=new_env_id,
        )

        return env_config_instance.env_id, True

    def env(self, env_id: str) -> Environment:
        env_config_instance = self.get_existing_inflight_env_by_id(env_id)
        return env_config_instance.env

    def status(self, env_id: str) -> ServicesComposeState:
        execution_envs = dict(os.environ)
        for env_name in self._started_envs:
            if self._started_envs[env_name]['env_id'] == env_id:
                execution_envs['COMPOSE_FILE'] = \
                    self._started_envs[env_name]['params']['compose_files']
        services_status = dc_state(env=execution_envs, root=self.in_docker_project_root_path)

        return services_status
