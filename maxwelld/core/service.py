import os
import shlex
import sys
import warnings
from itertools import groupby
from pathlib import Path
from uuid import uuid4

from maxwelld.core.utils.compose_instance_cfg import get_absolute_compose_files
from maxwelld.core.utils.compose_instance_cfg import made_up_instance_compose_files

from maxwelld.core.utils.compose_instance_cfg import get_service_map

from maxwelld.helpers.bytes_pickle import base64_pickled

from maxwelld.env_description.env_types import Service

from maxwelld.core.utils.compose_files import parse_docker_compose

from maxwelld.helpers.bytes_pickle import debase64_pickled
from rich.text import Text

from maxwelld.client.types import EnvironmentId
from maxwelld.core.compose_data_types import ServicesComposeState
from maxwelld.core.compose_instance import ComposeInstanceProvider
from maxwelld.core.compose_interface import ComposeShellInterface
from maxwelld.core.config import Config
from maxwelld.core.sequence_run_types import EMPTY_ID
from maxwelld.core.utils.compose_files import scan_for_compose_files
from maxwelld.core.utils.compose_instance_cfg import get_new_env_id
from maxwelld.core.utils.env_files import make_debug_bash_env
from maxwelld.env_description.env_types import Environment
from maxwelld.helpers.exec_record import ExecRecord
from maxwelld.helpers.jobs_result import JobResult
from maxwelld.helpers.labels import Label
from maxwelld.output.console import CONSOLE
from maxwelld.output.styles import Style




class MaxwellDemonService:
    def __init__(self,
                 config=Config,
                 compose_interface: type[ComposeShellInterface] = None,
                 compose_instance_maker: type[ComposeInstanceProvider] = None):
        # assert shutil.which("docker"), 'Docker not installed'
        # assert shutil.which("docker-compose"), 'Docker-compose not installed'

        # assert os.environ.get('COMPOSE_PROJECT_NAME'), \
        #     'COMPOSE_PROJECT_NAME env should be set'
        # assert os.environ.get('NON_STOP_CONTAINERS'), \
        #     'NON_STOP_CONTAINERS env should be set'
        # assert os.environ.get('HOST_PROJECT_ROOT_DIRECTORY'), \
        #     'HOST_PROJECT_ROOT_DIRECTORY env should be set'

        # TODO print service paths for *.yml files, project root and etc.
        cfg = config()
        self._project = cfg.project
        self._non_stop_containers = cfg.non_stop_containers
        self.tmp_envs_path = cfg.tmp_envs_path
        self.in_docker_project_root_path = cfg.in_docker_project_root_path
        self.env_file_name = cfg.env_file_name
        self.env_file_path = cfg.env_file_path
        self.host_project_root_directory = cfg.host_project_root_directory
        self.env_tmp_directory = cfg.env_tmp_directory
        self.host_env_tmp_directory = cfg.host_env_tmp_directory
        self.execs: dict[str, ExecRecord] = {}

        self._compose_interface = ComposeShellInterface
        if compose_interface is not None:
            self._compose_interface = compose_interface

        if compose_instance_maker is None:
            compose_instance_maker = ComposeInstanceProvider

        self._compose_instance_manager = compose_instance_maker(
            project=self._project,
            compose_interface=self._compose_interface,
            except_containers=self._non_stop_containers,
            in_docker_project_root=self.in_docker_project_root_path,
            host_project_root_directory=self.host_project_root_directory,
            tmp_envs_path=self.tmp_envs_path,
        )

    def _unpack_services_env_template_params(self, env: Environment):
        return {service: env[service].env for service in env}

    async def up_compose(self, name: str, config_template: Environment, compose_files: str, isolation=None,
                         parallelism_limit=None, verbose=False, force_restart=False) -> tuple[EnvironmentId, bool]:
        warnings.warn('Deprecated, use up_or_get_existing instead')
        return await self.up_or_get_existing(
            name, config_template, compose_files, isolation, parallelism_limit, verbose, force_restart
        )

    async def _get_existing(self, name: str, config_template: Environment | None, compose_files: str | None):
        services_state = await self._compose_instance_manager.make_system().get_active_services_state()
        services_states = services_state.get_all_for(
            lambda service_state: (
                service_state.check(Label.REQUEST_ENV_NAME, str(name))
                and service_state.check(Label.ENV_CONFIG_TEMPLATE, base64_pickled(config_template))
                and service_state.check(Label.COMPOSE_FILES, compose_files)
            )
        )

        if not services_states.as_json():
            return None

        resul_service = services_states.get_any_for(Label.REQUEST_ENV_NAME, name)
        env_id = resul_service.labels.get(Label.ENV_ID, None)

        # check all up or ok-exited
        map_service = get_service_map(config_template, env_id)
        services_names = dict(groupby(services_states.as_json(), lambda x: x['name']))
        for service_name in set(config_template.get_services()) - set(self._non_stop_containers):
            mapped_name = map_service.get(service_name, None)
            if mapped_name not in services_names:
                CONSOLE.print(f"Service {service_name} isn't ready")
                # TODO filter ok exited containers
                return None


        CONSOLE.print(f'Existing env for {name}: {env_id}. Access: '
                      f'> cd {self.host_project_root_directory} && '
                      f'source ./env-tmp/{env_id}/.env')
        return env_id

    async def up_or_get_existing(
        self, name: str, config_template: Environment | None, compose_files: str | None, isolation=None,
        parallelism_limit=None,
        verbose=False,
        force_restart: bool = False,
        release_id: str = None,
    ) -> tuple[EnvironmentId, bool]:

        if not compose_files:
            # default docker compose files
            compose_files = ':'.join(
                scan_for_compose_files(self.in_docker_project_root_path)
            )

        if not config_template:
            # default config template
            config_template = Environment(
                'AUTO_SCANNED_FULL',

                *[Service(name) for name in parse_docker_compose(
                    get_absolute_compose_files(compose_files, self.in_docker_project_root_path),
                )]
            )

        existing_inflight_env_id = await self._get_existing(name, config_template, compose_files)
        # TODO check all services up (makes now on client side)
        if existing_inflight_env_id and not force_restart:
            CONSOLE.print(
                Text('Found suitable ready env: ', style=Style.info)
                .append(Text(name, style=Style.mark))
            )
            return existing_inflight_env_id, False

        CONSOLE.print(
            Text('Starting new environment: ', style=Style.info)
            .append(Text(name, style=Style.mark))
        )

        new_env_id = get_new_env_id()
        if release_id is None:
            release_id = str(uuid4())

        if parallelism_limit == 1:
            CONSOLE.print(f'Using default service names with {parallelism_limit=}')
            new_env_id = EMPTY_ID

        target_compose_instance = self._compose_instance_manager.make(
            new_env_id,
            name=name,
            compose_files=compose_files or ':'.join(scan_for_compose_files(self.in_docker_project_root_path)),
            config_template=config_template,
            release_id=release_id,
        )

        system_instance_manager = self._compose_instance_manager.make_system()
        if parallelism_limit == 1:
            # check if limit 1 - existing already not fit - down all current inflight
            instances_to_down = await system_instance_manager.get_active_services_state()
            env_ids = filter(
                lambda x: x,
                [
                    instance_to_down.as_json()['labels'].get(Label.SERVICE_TEMPLATE_NAME, None)
                    for instance_to_down in instances_to_down
                ]
            )
            await self._compose_instance_manager.make_system().down(env_ids)
            # TODO check if > 1
            #          check current {name} is runnig?
            #              runnig -> current {name} to down list
            #              check curren - 1 > limit
            #                   grab to down some of limit - (current - 1)

        await target_compose_instance.cleanup()
        await target_compose_instance.run()
        target_compose_instance_files = target_compose_instance.compose_instance_files

        make_debug_bash_env(target_compose_instance_files, self.host_env_tmp_directory)
        CONSOLE.print(f'Docker-compose access: > cd {self.host_project_root_directory} && '
                      f'source ./env-tmp/{new_env_id}/.env')

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

        return new_env_id, True

    async def env(self, env_id: str) -> Environment | None:
        system_instance_manager = self._compose_instance_manager.make_system()
        services = await system_instance_manager.get_active_services_state()
        CONSOLE.print(f'get_env {env_id}:')

        CONSOLE.print(services.as_json())
        service_state = services.get_any_for(Label.ENV_ID, env_id)

        # CONSOLE.print(service_state.as_json())
        if service_state:
            env_config = service_state.labels.get(Label.ENV_CONFIG, None)
            return debase64_pickled(env_config)

        return None

    async def status(self, env_id: str) -> ServicesComposeState:
        system_instance_manager = self._compose_instance_manager.make_system()
        services = await system_instance_manager.get_active_services_state()
        services_status = services.get_all_for(lambda service_state: service_state.check(Label.ENV_ID, env_id))

        assert isinstance(services_status, ServicesComposeState), "Can't execute docker-compose ps"
        return services_status

    async def exec(self, env_id: str, container: str, command: str, detached: bool = False):
        uid = str(uuid4())
        log_file = f'{uid}.log'
        self.execs = {uid: ExecRecord(env_id, container, log_file)}

        system_instance_manager = self._compose_instance_manager.make_system()
        services = await system_instance_manager.get_active_services_state()
        service_status = services.get_any_for(Label.ENV_ID, env_id)

        env_compose_files = service_status.labels.get(Label.COMPOSE_FILES)

        compose_interface = self._compose_interface(
            compose_files=env_compose_files,
            in_docker_project_root=self.in_docker_project_root_path
        )

        detached_str = ' &' if detached else ''
        cmd = f'sh -c \'{shlex.quote(command)[1:-1]} > /tmp/{log_file} 2>&1 {detached_str}\''
        await compose_interface.dc_exec(container, cmd)

        job_result, stdout, stderr = await compose_interface.dc_exec(container, f'cat /tmp/{log_file}')
        if job_result != JobResult.GOOD:
            ...

        return uid, stdout

    async def get_exec_logs(self, uid: str):
        if uid not in self.execs:
            return b''

        exec_record = self.execs[uid]

        system_instance_manager = self._compose_instance_manager.make_system()
        services = await system_instance_manager.get_active_services_state()
        service_status = services.get_any_for(Label.ENV_ID, exec_record.env_id)

        env_compose_files = service_status.labels.get(Label.COMPOSE_FILES)

        compose_interface = self._compose_interface(
            compose_files=env_compose_files,
            in_docker_project_root=self.in_docker_project_root_path
        )

        job_result, stdout, stderr = await compose_interface.dc_exec(
            exec_record.container,
            f'cat /tmp/{exec_record.log_file}'
        )
        if job_result != JobResult.GOOD:
            ...

        return stdout

    async def logs(self, env_id: str, services: list[str]) -> dict[str, bytes]:
        system_instance_manager = self._compose_instance_manager.make_system()
        services_state = await system_instance_manager.get_active_services_state()
        service_status = services_state.get_any_for(Label.ENV_ID, env_id)

        env_compose_files = service_status.labels.get(Label.COMPOSE_FILES)

        compose_interface = self._compose_interface(
            compose_files=env_compose_files,
            in_docker_project_root=self.in_docker_project_root_path
        )

        logs = {}
        for service in services:
            job_result, log = await compose_interface.dc_logs([service])
            logs[service] = log
            if job_result != JobResult.GOOD:
                ...

        return logs


class MaxwellDemonServiceManager:
    maxwell_demon_service = None

    def __init__(self):
        if MaxwellDemonServiceManager.maxwell_demon_service is None:
            MaxwellDemonServiceManager.maxwell_demon_service = MaxwellDemonService()

    def get(self) -> MaxwellDemonService:
        return MaxwellDemonServiceManager.maxwell_demon_service
