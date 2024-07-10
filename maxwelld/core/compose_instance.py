import os
import sys
from pathlib import Path

from rich.text import Text

from maxwelld.env_description.env_types import Environment
from maxwelld.core.compose_interface import ComposeShellInterface
from maxwelld.core.sequence_run_types import ComposeInstanceFiles
from maxwelld.core.sequence_run_types import EMPTY_ID
from maxwelld.core.sequence_run_types import EnvInstanceConfig
from maxwelld.core.utils.compose_files import make_env_compose_instance_files
from maxwelld.core.utils.compose_files import get_compose_services
from maxwelld.core.utils.compose_instance_cfg import get_new_instance_compose_files
from maxwelld.core.utils.compose_instance_cfg import make_env_instance_config
from maxwelld.env_description.env_types import EventStage
from maxwelld.helpers.jobs_result import JobResult
from maxwelld.output.console import CONSOLE
from maxwelld.output.styles import Style

INFLIGHT = 'inflight'


class ComposeInstance:
    def __init__(self,
                 project: str,
                 new_env_id: str,
                 compose_interface: type[ComposeShellInterface],
                 compose_files: str,
                 compose_files_path: Path,
                 config_template: Environment | None,
                 in_docker_project_root: Path,
                 host_project_root_directory: Path,
                 except_containers: list[str],
                 tmp_envs_path: Path,
                 execution_envs: dict = None):
        self.compose_files = compose_files
        self.compose_files_path = compose_files_path
        self.in_docker_project_root = in_docker_project_root
        self.host_project_root_directory = host_project_root_directory
        self.except_containers = except_containers
        self.tmp_envs_path = tmp_envs_path

        self.project = project
        if execution_envs is None:
            self.execution_envs = dict(os.environ)

        self.new_env_id = new_env_id
        self.config_template = config_template
        self._env_instance_config = None
        self.compose_interface = compose_interface

        self.compose_instance_files = None
        for file in self.compose_files.split(':'):
            assert (file := Path(self.compose_files_path / file)).exists(), f'File {file} doesnt exist'

        print('ComposeInstance:')
        print(self.compose_files)
        print(self.compose_files_path)
        print()

    async def config(self) -> EnvInstanceConfig:
        if self._env_instance_config is None:
            self._env_instance_config = make_env_instance_config(
                env_template=self.config_template,
                env_id=self.new_env_id
            )
        return self._env_instance_config

    async def generate_config_files(self) -> ComposeInstanceFiles:
        assert self.new_env_id != INFLIGHT, 'somehow u try to regenerate files for inflight env'
        compose_instance_files = make_env_compose_instance_files(
            await self.config(),
            self.compose_files,
            project_network_name=self.project,
            host_project_root_directory=self.host_project_root_directory,
            compose_files_path=self.compose_files_path,
            tmp_env_path=self.tmp_envs_path,
        )
        # TODO uneven compose_executor initialization!! but compose_interface compose_files-dependent
        self.compose_executor = self.compose_interface(
            compose_files=compose_instance_files.compose_files,
            in_docker_project_root=self.in_docker_project_root,
        )
        return compose_instance_files

    async def run(self):
        self.compose_instance_files = compose_instance_files = await self.generate_config_files()

        # TODO get services from dc
        services = get_compose_services(self.compose_instance_files.compose_files)
        if compose_instance_files.env_config_instance.env_services_map:
            services = list(compose_instance_files.env_config_instance.env_services_map.values())

        CONSOLE.print(
            Text('Starting services: ', style=Style.info)
            .append(Text(str(services), style=Style.good))
        )
        if compose_instance_files.env_config_instance.env_id == EMPTY_ID:
            for container in self.except_containers:
                if container in services:
                    services.remove(container)
            print(f'Starting services except original {self.except_containers} already started: {services}')

        status_result = await self.compose_executor.dc_state()
        assert status_result != JobResult.BAD, f"Can't get first status for services {services}"

        # TODO startup plan with dependencies
        up_result = await self.compose_executor.dc_up(services)
        assert up_result == JobResult.GOOD, f"Can't up services {services}"

        # run after service and after all hooks
        # TODO move after service, after service up
        for current_stage in [EventStage.BEFORE_ALL, EventStage.BEFORE_SERVICE_START,
                              EventStage.AFTER_SERVICE_START, EventStage.AFTER_ALL]:
            for service in compose_instance_files.env_config_instance.env:
                for handler in compose_instance_files.env_config_instance.env[service].events_handlers + \
                               compose_instance_files.inline_migrations[service]:
                    if handler.stage != current_stage:
                        continue

                    # TODO check target service substitution
                    target_service = compose_instance_files.env_config_instance.env_services_map[
                        handler.executor or service]
                    substituted_cmd = handler.cmd % compose_instance_files.env_config_instance.env_services_map

                    migrate_result = await self.compose_executor.dc_exec(target_service, substituted_cmd)
                    assert migrate_result == JobResult.GOOD, (f"Can't migrate service {target_service}, "
                                                              f"with {substituted_cmd}")


class ComposeInstanceManager:
    def __init__(self, project: str, compose_interface: type[ComposeShellInterface], except_containers: list[str],
                 compose_files_path: Path, default_compose_files: str, in_docker_project_root: Path,
                 host_project_root_directory: Path,
                 tmp_envs_path: Path):
        self.project = project
        self.compose_interface = compose_interface
        self.except_containers = except_containers
        self.compose_files_path = compose_files_path
        self.default_compose_files = default_compose_files
        self.in_docker_project_root = in_docker_project_root
        self.host_project_root_directory = host_project_root_directory
        self.tmp_envs_path = tmp_envs_path

    def make(self, new_env_id: str, compose_files: str | None, config_template: Environment, ):
        return ComposeInstance(
            project=self.project,
            compose_interface=self.compose_interface,
            new_env_id=new_env_id,
            compose_files=compose_files if compose_files else self.default_compose_files,
            compose_files_path=self.compose_files_path,
            config_template=config_template,
            in_docker_project_root=self.in_docker_project_root,
            host_project_root_directory=self.host_project_root_directory,
            except_containers=self.except_containers,
            tmp_envs_path=self.tmp_envs_path,
        )

    def from_compose_instance_files(self, compose_files: str | None, config_template: Environment, ):
        return ComposeInstance(
            project=self.project,
            compose_interface=self.compose_interface,
            new_env_id=INFLIGHT,
            compose_files=compose_files if compose_files else self.default_compose_files,
            compose_files_path=self.compose_files_path,
            config_template=config_template,
            in_docker_project_root=self.in_docker_project_root,
            host_project_root_directory=self.host_project_root_directory,
            except_containers=self.except_containers,
            tmp_envs_path=self.tmp_envs_path,
        )

    def get_envs(self) -> list[str]:
        dirpath, dirnames, filenames = next(os.walk(self.tmp_envs_path))
        return dirnames

    async def down_env(self, env_id):
        dirpath, dirnames, filenames = next(os.walk(self.tmp_envs_path / env_id))
        if '.env' in filenames:
            filenames.remove('.env')
        docker_files = get_new_instance_compose_files(':'.join(filenames), self.tmp_envs_path / env_id)

        services = get_compose_services(docker_files)
        print(f'Down services: {services}, except {self.except_containers}')
        for container in self.except_containers:
            if container in services:
                services.remove(container)

        compose_executor = self.compose_interface(
            compose_files=docker_files,
            in_docker_project_root=self.in_docker_project_root,
        )
        down_result = await compose_executor.dc_down(services)
        assert down_result == JobResult.GOOD, (f"Can't down services {services}")
