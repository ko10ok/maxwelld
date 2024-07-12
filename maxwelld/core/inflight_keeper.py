import os
import shutil
from copy import deepcopy
from pathlib import Path
from typing import Union

from rich import json

from maxwelld.client.types import EnvironmentId
from maxwelld.core.sequence_run_types import EMPTY_ID
from maxwelld.core.sequence_run_types import EnvInstanceConfig
from maxwelld.core.utils.compose_instance_cfg import make_env_instance_config
from maxwelld.env_description.env_types import Environment
from maxwelld.helpers.bytes_pickle import base64_pickled
from maxwelld.helpers.bytes_pickle import debase64_pickled


class InflightKeeper:
    def __init__(self, tmp_envs_path: Path, env_file_name: str):
        self.tmp_envs_path = tmp_envs_path
        self.env_file_name = env_file_name
        self._started_envs: dict = {}
        self._envs_file_path = self.tmp_envs_path / self.env_file_name

    def cleanup_in_flight(self):
        if os.path.exists(self._envs_file_path):
            with open(self._envs_file_path, 'r') as envs_file:
                envs_ = envs_file.read()
                if not envs_:
                    envs_ = '{}'
                return json.loads(envs_)

        self.tmp_envs_path.mkdir(parents=True, exist_ok=True)
        dirpath, dirnames, filenames = next(os.walk(self.tmp_envs_path))
        for dir in dirnames:
            # TODO execute dc down for each env folder
            # TODO remove file interference (2 jobs on same runner will write/read same file)
            shutil.rmtree(Path(dirpath) / dir)

    def get_existing_inflight_env(self, name: str, config_template: Environment | None,
                                  compose_files: str) -> Union[EnvInstanceConfig, None]:
        if name in self._started_envs:
            env_id = self._started_envs[name]['env_id']
            env_config_instance = make_env_instance_config(
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

    def update_inflight_envs(self, name, config_template: Environment, compose_files: str, env_id: str):
        self._started_envs[name] = {
            'env_id': env_id,
            'params': {
                'name': name,
                'compose_files': compose_files,
                'config_template': base64_pickled(config_template)
            }
        }

        with open(self._envs_file_path, 'w') as envs_file:
            envs_file.write(
                json.dumps(self._started_envs)
            )  # TODO fix sync when env upped but no record or record exists but bo env

    def check_env_limits(self) -> list[dict]:
        in_flight = deepcopy(self._started_envs)
        to_delete = []
        for env_name, env_params in in_flight.items():
            if env_params['env_id'] == EMPTY_ID:  # different env starts EMPTY_ID
                # down_in_flight_envs(
                #     self.tmp_envs_path,
                #     EMPTY_ID,
                #     self.in_docker_project_root_path,
                #     except_containers=self._non_stop_containers
                # )
                to_delete += [in_flight[env_name]]
                del self._started_envs[env_name]
        return to_delete

    def get_existing_inflight_env_by_id(self, env_id: EnvironmentId) -> Union[EnvInstanceConfig, None]:
        for env_name in self._started_envs:
            if self._started_envs[env_name]['env_id'] == env_id:
                config_template = debase64_pickled(self._started_envs[env_name]['params']['config_template'])
                env_config_instance = make_env_instance_config(
                    env_template=config_template,
                    env_id=env_id
                )
                return env_config_instance
        return None

    def get_existing_inflight_env_compose_files(self, env_id: EnvironmentId) -> Union[EnvInstanceConfig, None]:
        from pprint import pprint
        pprint(self._started_envs)
        for env_name in self._started_envs:
            if self._started_envs[env_name]['env_id'] == env_id:
                return self._started_envs[env_name]['params']['compose_files']
        return None
