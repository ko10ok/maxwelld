import json
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from uuid import uuid4
from warnings import warn

from rich.text import Text

from maxwelld.client.types import EnvironmentId
from maxwelld.core.compose_files_utils import extract_services_inline_migration
from maxwelld.core.compose_files_utils import patch_docker_compose_file_services
from maxwelld.core.compose_files_utils import read_dc_file
from maxwelld.core.compose_interface import dc_exec
from maxwelld.core.compose_interface import dc_state
from maxwelld.core.compose_interface import dc_up
from maxwelld.core.sequence_run_types import EMPTY_ID
from maxwelld.core.sequence_run_types import EnvConfigComposeInstance
from maxwelld.core.sequence_run_types import EnvConfigInstance
from maxwelld.env_description.env_types import Env
from maxwelld.env_description.env_types import Environment
from maxwelld.env_description.env_types import EventStage
from maxwelld.env_description.env_types import Service
from maxwelld.env_description.env_types import ServiceMode
from maxwelld.output.console import CONSOLE
from maxwelld.output.styles import Style
from maxwelld.vedro_plugin.state_waiting import JobResult


def make_env_service_name(service, env_id):
    if env_id == EMPTY_ID:
        return service
    return f'{service}-{env_id}'


def sub_env_id(env: Env, services_for_env) -> Env:
    result_env = Env()
    for k, v in env.items():
        # TODO split environments by services
        try:
            res = v.format(**services_for_env)
            result_env.update({k: res})
        except KeyError:
            # temporarily suppressed
            # warn(f'cant substitute key: {k} for value: {v}, with {services_for_env}')
            ...

    return result_env


def prepare_services_env(env: Environment, services_map: dict) -> Environment:
    updated_services = []
    for service_name in env:
        updated_services += [
            Service(
                name=env[service_name].name,
                env=sub_env_id(env[service_name].env, services_map),
                events_handlers=env[service_name].events_handlers,
                mode=env[service_name].mode,
            )
        ]
    new_env = Environment(str(env), *updated_services)
    return new_env


def get_new_env_id() -> EnvironmentId:
    env_id = str(uuid4())[:4]
    return env_id


def get_service_map(env: Environment, new_env_id: str):
    return {
        service_name: make_env_service_name(service_name, new_env_id)
        for service_name, service in env.get_services().items() if service.mode != ServiceMode.OFF
    }


def make_env_config_instance(env_template: Environment, env_id) -> EnvConfigInstance:
    services_map = get_service_map(env_template, env_id)
    return EnvConfigInstance(
        env_source=env_template,
        env_id=env_id,
        env_services_map=services_map,
        env=prepare_services_env(env_template, services_map)
    )


def get_new_instance_compose_files(compose_files: str, env_directory: Path) -> str:
    return ':'.join(
        [
            str(env_directory / compose_file)
            for compose_file in compose_files.split(':')
        ]
    )


def get_compose_services(compose_files: str):
    services = []
    for filename in compose_files.split(':'):
        dc_cfg = read_dc_file(filename)
        if 'services' in dc_cfg:
            for service in dc_cfg['services'].keys():
                if service not in services:
                    services += [service]
    return services


def make_env_compose_instance_files(env_config_instance: EnvConfigInstance,
                                    compose_files: str,
                                    project_network_name: str,  # without "_default"
                                    host_project_root_directory,
                                    compose_files_path: Path,
                                    tmp_env_path: Path,
                                    ) -> EnvConfigComposeInstance:
    dst = tmp_env_path / env_config_instance.env_id
    dst.mkdir(parents=True, exist_ok=True)

    for file in compose_files.split(':'):
        src_file = compose_files_path / file
        dst_file = dst / file
        shutil.copy(src_file, dst_file)

        # TODO fill dc files with env from .envs files as default
        patch_docker_compose_file_services(
            dst_file,
            host_root=host_project_root_directory,
            services_environment_vars=env_config_instance.env,
            network_name=f'{project_network_name}_default',
            services_map=env_config_instance.env_services_map
        )

    new_compose_files_list = get_new_instance_compose_files(compose_files, dst)

    inline_migrations = extract_services_inline_migration(new_compose_files_list.split(':'))

    return EnvConfigComposeInstance(
        env_config_instance=env_config_instance,
        compose_files_source=compose_files,
        directory=dst,
        compose_files=new_compose_files_list,
        inline_migrations=inline_migrations,
    )


def make_debug_bash_env(env_config_compose_instance: EnvConfigComposeInstance,
                        host_tmp_env_path: Path):
    new_external_compose_file = get_new_instance_compose_files(
        env_config_compose_instance.compose_files_source,
        host_tmp_env_path / env_config_compose_instance.env_config_instance.env_id
    )

    with open(env_config_compose_instance.directory / '.env', 'w') as f:
        f.write(f'alias dc="docker-compose --project-directory ."\n')
        f.write(f'export COMPOSE_FILE={new_external_compose_file}\n')
        f.write(f'alias deactivate-env="unset COMPOSE_FILE"\n')
        # TODO Envs
        # for k,value in updated_envs.items():
        #     f.write(f'{k}={value}\n')
        # f.write(f'export COMPOSE_PROJECT_NAME={new_project_name}\n')


# TODO move into compose_interface.py
def print_state(execution_envs, in_docker_project_root):
    status = subprocess.call(
        shlex.split(
            "docker-compose --project-directory . ps -a --format='table "
            "{{.Service}}\t{{.ExitCode}}\t{{.Health}}\t{{.Image}}\t{{.State}}\t{{.Status}}'"
        ),
        env=execution_envs,
        cwd=in_docker_project_root
    )
    assert status == 0, 'Не смогли получить стейт'  # TODO make error type + dc down  or в diagnostic mode


async def run_env(dc_env_config: EnvConfigComposeInstance, in_docker_project_root, except_containers: list[str]):
    services = list(dc_env_config.env_config_instance.env_services_map.values())
    CONSOLE.print(
        Text('Starting services: ', style=Style.info)
        .append(Text(str(services), style=Style.good))
    )
    if dc_env_config.env_config_instance.env_id == EMPTY_ID:
        for container in except_containers:
            if container in services:
                services.remove(container)
        print(f'Starting services except original {except_containers} already started: {services}')

    execution_envs = dict(os.environ)
    execution_envs['COMPOSE_FILE'] = dc_env_config.compose_files

    status_result = await dc_state(execution_envs, in_docker_project_root)
    assert status_result != JobResult.BAD, f"Can't get first status for services {services}"

    up_result = await dc_up(services, execution_envs, in_docker_project_root)
    assert up_result == JobResult.GOOD, f"Can't up services {services}"

    # run after servoice and after all hooks
    # TODO move after service, after service up
    for current_stage in [EventStage.BEFORE_ALL, EventStage.BEFORE_SERVICE_START, EventStage.AFTER_SERVICE_START, EventStage.AFTER_ALL]:
        for service in dc_env_config.env_config_instance.env:
            for handler in dc_env_config.env_config_instance.env[service].events_handlers + dc_env_config.inline_migrations[service]:
                if handler.stage != current_stage:
                    continue

                # TODO check target service substitution
                target_service = dc_env_config.env_config_instance.env_services_map[handler.executor or service]
                substituted_cmd = handler.cmd % dc_env_config.env_config_instance.env_services_map

                migrate_result = await dc_exec(target_service, substituted_cmd, execution_envs, in_docker_project_root)
                assert migrate_result == JobResult.GOOD, (f"Can't migrate service {target_service}, "
                                                          f"with {substituted_cmd}")


# TODO move into compose_interface.py
def down_in_flight_envs(tmp_envs_path: Path, env_id, in_docker_project_root, except_containers: list[str]):
    dirpath, dirnames, filenames = next(os.walk(tmp_envs_path / env_id))
    filenames.remove('.env')
    docker_files = get_new_instance_compose_files(':'.join(filenames),
                                                  tmp_envs_path / env_id)

    execution_envs = dict(os.environ)
    execution_envs['COMPOSE_FILE'] = docker_files

    services = get_compose_services(docker_files)
    print(f'Down services: {services}, except {except_containers}')
    for container in except_containers:
        if container in services:
            services.remove(container)
    down = subprocess.call(
        ['docker-compose', '--project-directory', '.', 'down', *services],
        env=execution_envs,
        cwd=in_docker_project_root
    )
    # TODO make error type + dc down  or в diagnostic mode
    if down != 0:
        print('Не смогли прибить все поднятое')
        print_state(execution_envs, in_docker_project_root)
        sys.exit(down)


def setup_env_for_tests(env: Environment):
    updated_env = {}
    for service in env:
        for k, v in env[service].env.items():
            if k in updated_env and updated_env[k] != v:
                warn(
                    f'⚠️ env {k} tried to setup up multiple'
                    f' times with different values: {updated_env[k]} vs {v}'
                )
            updated_env[k] = v
            os.environ[k] = v


def unpack_services_env_template_params(env: Environment):
    return {service: env[service].env for service in env}


def actualize_in_flight(tmp_envs_path: Path, env_file_name: str) -> {}:
    env_file_path = tmp_envs_path / env_file_name

    if os.path.exists(env_file_path):
        with open(env_file_path, 'r') as envs_file:
            envs_ = envs_file.read()
            if not envs_:
                envs_ = '{}'
            return json.loads(envs_)

    dirpath, dirnames, filenames = next(os.walk(tmp_envs_path))
    for dir in dirnames:
        # TODO execute dc down for each env folder
        # TODO remove file interference (2 jobs on same runner will write/read same file)
        shutil.rmtree(Path(dirpath) / dir)
    return {}
