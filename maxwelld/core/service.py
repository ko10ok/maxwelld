import os
import shutil

from rich.text import Text

from maxwelld.client.types import EnvironmentId
from maxwelld.core.compose_data_types import ServicesComposeState
from maxwelld.core.compose_instance import ComposeInstanceManager
from maxwelld.core.compose_interface import ComposeShellInterface
from maxwelld.core.config import Config
from maxwelld.core.inflight_keeper import InflightKeeper
from maxwelld.core.sequence_run_types import EMPTY_ID
from maxwelld.core.utils.compose_instance_cfg import get_new_env_id
from maxwelld.core.utils.env_files import make_debug_bash_env
from maxwelld.env_description.env_types import Environment
from maxwelld.output.console import CONSOLE
from maxwelld.output.styles import Style


class MaxwellDemonService:
    def __init__(self,
                 cfg=Config,
                 compose_interface: ComposeShellInterface = None,
                 inflight_keeper: InflightKeeper = None,
                 compose_instance_maker: ComposeInstanceManager = None):
        assert shutil.which("docker"), 'Docker not installed'
        assert shutil.which("docker-compose"), 'Docker-compose not installed'

        assert os.environ.get('COMPOSE_PROJECT_NAME'), \
            'COMPOSE_PROJECT_NAME env should be set'
        assert os.environ.get('NON_STOP_CONTAINERS'), \
            'NON_STOP_CONTAINERS env should be set'
        assert os.environ.get('HOST_PROJECT_ROOT_DIRECTORY'), \
            'HOST_PROJECT_ROOT_DIRECTORY env should be set'

        # TODO print service paths for *.yml files, project root and etc.
        self._project = cfg.project
        self._non_stop_containers = cfg.non_stop_containers
        self.tmp_envs_path = cfg.tmp_envs_path
        self.compose_files_path = cfg.compose_files_path
        self.in_docker_project_root_path = cfg.in_docker_project_root_path
        self.env_file_name = cfg.env_file_name
        self.env_file_path = cfg.env_file_path
        self.host_project_root_directory = cfg.host_project_root_directory
        self.env_tmp_directory = cfg.env_tmp_directory
        self.host_env_tmp_directory = cfg.host_env_tmp_directory

        if compose_interface is None:
            self._compose_interface = ComposeShellInterface

        if compose_instance_maker is None:
            self._compose_instance_manager = ComposeInstanceManager(
                project=self._project,
                compose_interface=self._compose_interface,
                except_containers=self._non_stop_containers,
                compose_files_path=cfg.compose_files_path,
                in_docker_project_root=self.in_docker_project_root_path,
                host_project_root_directory=self.host_project_root_directory,
            )

        if inflight_keeper is None:
            self._inflight_keeper = InflightKeeper(self.tmp_envs_path, self.env_file_name)

        self._inflight_keeper.cleanup_in_flight()

    def _unpack_services_env_template_params(self, env: Environment):
        return {service: env[service].env for service in env}

    async def up_compose(
        self, name: str, config_template: Environment, compose_files: str, isolation=None, parallelism_limit=None,
        verbose=False, force_restart: bool = False
    ) -> tuple[EnvironmentId, bool]:

        existing_inflight_env = self._inflight_keeper.get_existing_inflight_env(
            name, config_template, compose_files
        )
        if existing_inflight_env and not force_restart:
            CONSOLE.print(f'Existing env for {name}: {existing_inflight_env.env_id}. Access: '
                          f'> cd {self.host_project_root_directory} && '
                          f'source ./env-tmp/{existing_inflight_env.env_id}/.env')
            return existing_inflight_env.env_id, False

        CONSOLE.print(
            Text('Starting new environment: ', style=Style.info)
            .append(Text(name, style=Style.mark))
        )

        new_env_id = get_new_env_id()
        target_compose_instance = self._compose_instance_manager.make(
            new_env_id,
            compose_files=compose_files,
            config_template=config_template,
        )
        if parallelism_limit == 1:
            # check if limit 1 - existing already not fit - down all current inflight
            CONSOLE.print(f'Using default service names with {parallelism_limit=}')
            new_env_id = EMPTY_ID
            to_down = self._compose_instance_manager.get_envs()
            for instance in to_down:
                self._compose_instance_manager.down_env(instance)
                self._inflight_keeper.cleanup_in_flight()
                # TODO check if > 1
                #          check current {name} is runnig?
                #              runnig -> current {name} to down list
                #              check curren - 1 > limit
                #                   grab to down some of limit - (current - 1)

        make_debug_bash_env(target_compose_instance, self.host_env_tmp_directory)
        CONSOLE.print(f'Docker-compose access: > cd {self.host_project_root_directory} && '
                      f'source ./env-tmp/{new_env_id}/.env')

        await target_compose_instance.run_env()

        # TODO should be transactional with file
        CONSOLE.print(Text(f'New environment for {name} started'))
        if verbose:
            CONSOLE.print(
                f'Config params: {self._unpack_services_env_template_params(target_compose_instance.config().env)}'
            )
        CONSOLE.print(
            Text(f'Docker-compose access: > ', style=Style.info)
            .append(Text(
                f'cd {self.host_project_root_directory} && source ./env-tmp/{new_env_id}/.env',
                style=Style.mark_neutral))
        )

        self._inflight_keeper.update_inflight_envs(
            name,
            config_template=config_template,
            compose_files=target_compose_instance.compose_files,
            env_id=new_env_id,
        )

        return new_env_id, True

    def env(self, env_id: str) -> Environment:
        env_instance_config = self._inflight_keeper.get_existing_inflight_env_by_id(env_id)
        return env_instance_config.env

    async def status(self, env_id: str) -> ServicesComposeState:
        env_compose_files = self._inflight_keeper.get_existing_inflight_env_compose_files(env_id)
        services_status = await self._compose_interface(
            compose_files=env_compose_files,
            in_docker_project_root=self.in_docker_project_root_path
        ).dc_state()
        assert isinstance(services_status, ServicesComposeState), "Can't execute docker-compose ps"
        return services_status


class MaxwellDemonServiceManager:
    maxwell_demon_service = None

    def __init__(self):
        if MaxwellDemonServiceManager.maxwell_demon_service is None:
            MaxwellDemonServiceManager.maxwell_demon_service = MaxwellDemonService()

    def get(self) -> MaxwellDemonService:
        return MaxwellDemonServiceManager.maxwell_demon_service
