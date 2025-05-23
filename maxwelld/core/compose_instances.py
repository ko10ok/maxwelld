import os
from pathlib import Path

from maxwelld.core.compose_data_types import ServicesComposeState
from maxwelld.core.compose_interface import ComposeShellInterface
from maxwelld.core.sequence_run_types import ComposeInstanceFiles
from maxwelld.core.sequence_run_types import EnvInstanceConfig
from maxwelld.core.utils.compose_files import make_env_compose_instance_files
from maxwelld.core.utils.compose_instance_cfg import make_env_instance_config
from maxwelld.env_description.env_types import Environment

INFLIGHT = 'inflight'


class ComposeInstances:
    def __init__(self,
                 project: str,
                 compose_interface: type[ComposeShellInterface],
                 compose_files: str,
                 in_docker_project_root: Path,
                 host_project_root_directory: Path,
                 except_containers: list[str],
                 tmp_envs_path: Path,
                 execution_envs: dict = None,
                 ):
        self.compose_files = compose_files
        self.in_docker_project_root = in_docker_project_root
        self.host_project_root_directory = host_project_root_directory
        self.except_containers = except_containers
        self.tmp_envs_path = tmp_envs_path

        self.project = project
        if execution_envs is None:
            self.execution_envs = dict(os.environ)

        self.new_env_id = 'system'
        self._env_instance_config = None
        self.compose_interface = compose_interface

        self.compose_instance_files: ComposeInstanceFiles = None
        for file in self.compose_files.split(':'):
            assert (file := Path(self.in_docker_project_root / file)).exists(), f'File {file} doesnt exist'

    async def config(self) -> EnvInstanceConfig:
        if self._env_instance_config is None:
            self._env_instance_config = make_env_instance_config(
                env_template=Environment('MAXWELLD_SYSTEM_DEFAULT'),
                env_id=self.new_env_id
            )
        return self._env_instance_config

    async def generate_config_files(self) -> ComposeInstanceFiles:
        compose_instance_files = make_env_compose_instance_files(
            await self.config(),
            self.compose_files,
            project_network_name=self.project,
            host_project_root_directory=self.host_project_root_directory,
            compose_files_path=self.in_docker_project_root,
            tmp_env_path=self.tmp_envs_path,
        )
        # TODO uneven compose_executor initialization!! but compose_interface compose_files-dependent
        self.compose_executor = self.compose_interface(
            compose_files=compose_instance_files.compose_files,
            in_docker_project_root=self.in_docker_project_root,
        )
        return compose_instance_files

    async def get_active_services_state(self) -> ServicesComposeState:
        self.compose_instance_files = await self.generate_config_files()
        state = await self.compose_executor.dc_state()
        return state

    async def down(self, services: list[str]):
        self.compose_instance_files = await self.generate_config_files()
        services_to_stop = list(filter(lambda x: x not in self.except_containers, services))
        if services_to_stop:
            await self.compose_executor.dc_down(services_to_stop)
