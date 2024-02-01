import json
import os
import shutil

from copy import deepcopy
from pathlib import Path
from typing import Union

from .env_types import Environment
from .exec_types import EMPTY_ID
from .exec_types import EnvConfigInstance
from .up_new_env import actualize_in_flight
from .up_new_env import down_in_flight_envs
from .up_new_env import get_new_env_id
from .up_new_env import make_debug_bash_env
from .up_new_env import make_env_compose_instance_files
from .up_new_env import make_env_config_instance
from .up_new_env import run_env
from .up_new_env import unpack_services_env_template_params


class MaxwellDemonService:
    def __init__(self, project, non_stop_containers):
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
        # TODO save name, env and compose params and ID of started env| make possible to read back.
        self._started_envs[name] = {
            'env_id': env_id,
            # 'params': {
                # 'compose_files': compose_files,
                # 'dot_envs': '',
                # 'compose_envs': unpack_services_env_template_params(config_template)
            # }
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

    def up_compose(self, name: str, config_template: Environment, compose_files: str,
                   isolation=None, parallelism_limit=None, verbose=False) -> Environment:
        # Envs -> Env -> CheckExisting -> TestEnv -> ComposeFiles -> run()

        if existing_inflight_env := self.get_existing_inflight_env(
            name, config_template, compose_files
        ):
            if verbose:
                print(f'Existing env for {name}: {self._started_envs[name]},'
                      f' no need to start again')
                print(f'Config params:'
                      f' {unpack_services_env_template_params(existing_inflight_env.env)}')
                print(f'Docker-compose access: '
                      f'> source ./env-tmp/{existing_inflight_env.env_id}/.env')
            return existing_inflight_env.env

        print('Starting new environment: ', name)
        new_env_id = get_new_env_id()
        if parallelism_limit == 1:
            print(f'Using default service names with {parallelism_limit=}')
            new_env_id = EMPTY_ID

        if new_env_id == EMPTY_ID:
            in_flight = deepcopy(self._started_envs)
            for env_name, env_params in in_flight.items():
                if env_params == {'env_id': EMPTY_ID}:  # different env starts EMPTY_ID
                    down_in_flight_envs(self.tmp_envs_path, EMPTY_ID, self.in_docker_project_root_path, except_containers=self._non_stop_containers)
                    del self._started_envs[env_name]

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
        print(f'Docker-compose access: > source ./env-tmp/{new_env_id}/.env')

        # TODO uncomment
        in_flight_env = run_env(
            compose_files_instance, self.in_docker_project_root_path, self._non_stop_containers
        )


        # TODO should be transactional with file
        print(f'New environment for {name} started: ', compose_files_instance)
        if verbose:
            print(f'Config params: {unpack_services_env_template_params(env_config_instance.env)}')
        print(f'Docker-compose access: > source ./env-tmp/{new_env_id}/.env')

        self.update_inflight_envs(
            name,
            config_template=config_template,
            compose_files=compose_files_instance.compose_files,
            env_id=new_env_id,
        )

        return env_config_instance.env


class MaxwellDemonClient:
    def __init__(self, project, non_stop_containers):
        self._project = project
        self._non_stop_containers = non_stop_containers
        self._server = MaxwellDemonService(project, self._non_stop_containers)


    def up_compose(self, name, config_template: Environment, compose_files: str, isolation=None,
                   parallelism_limit=None, verbose=False) -> Environment:
        return self._server.up_compose(
            name, config_template, compose_files, isolation, parallelism_limit, verbose
        )

    def list_current_in_flight_envs(self, *args, **kwargs):
        raise NotImplementedError()

    def list_services(self, *args, **kwargs):
        raise NotImplementedError()
