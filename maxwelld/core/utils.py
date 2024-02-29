import json
import os
import shlex
import shutil
import subprocess
import sys
from copy import deepcopy
from functools import partial
from pathlib import Path
from uuid import uuid4
from warnings import warn

import yaml
from rich.text import Text

from maxwelld.client.types import EnvironmentId
from maxwelld.core.docker_compose_interface import dc_state
from maxwelld.env_description.env_types import AsIs
from maxwelld.env_description.env_types import ComposeStateHandler
from maxwelld.env_description.env_types import Env
from maxwelld.env_description.env_types import Environment
from maxwelld.env_description.env_types import EventStage
from maxwelld.env_description.env_types import FuncHandler
from maxwelld.env_description.env_types import Service
from maxwelld.env_description.env_types import ServiceMode
from maxwelld.core.exec_types import EMPTY_ID
from maxwelld.core.exec_types import EnvConfigComposeInstance
from maxwelld.core.exec_types import EnvConfigInstance
from maxwelld.output.console import CONSOLE
from maxwelld.output.styles import Style


def make_env_service_name(service, env_id):
    if env_id == EMPTY_ID:
        return service
    return f'{service}-{env_id}'


def read_dc_file(filename: str | Path) -> dict:
    with open(filename) as f:
        return yaml.load(f, Loader=yaml.FullLoader)


def write_dc_file(filename: str | Path, cfg: dict) -> None:
    with open(filename, 'w') as f:
        f.write(yaml.dump(cfg))


def patch_network(dc_cfg: dict, network_name) -> dict:
    new_dc_cfg = deepcopy(dc_cfg)
    if 'networks' not in new_dc_cfg:
        new_dc_cfg['networks'] = {}
    new_dc_cfg['networks']['e2e_back_network'] = {
        'name': network_name,
        'external': True,
    }

    for service in new_dc_cfg['services']:
        if 'network' not in new_dc_cfg['services'][service]:
            new_dc_cfg['services'][service]['networks'] = []
        new_dc_cfg['services'][service]['networks'] += ['e2e_back_network']
    return new_dc_cfg


def patch_service_volumes(volumes: list, root_path: str | Path) -> list:
    updated_volumes = []
    for volume in volumes:
        new_volume = volume
        if volume.startswith('.'):
            new_volume = volume.replace('.', str(root_path), 1)
        updated_volumes += [new_volume]
    return updated_volumes


def patch_services_volumes(dc_cfg: dict, root_path: str | Path) -> dict:
    new_dc_cfg = deepcopy(dc_cfg)
    for service in dc_cfg['services']:
        if 'volumes' in dc_cfg['services'][service]:
            updated_volumes = patch_service_volumes(
                dc_cfg['services'][service]['volumes'],
                root_path
            )
            new_dc_cfg['services'][service]['volumes'] = updated_volumes
    return new_dc_cfg


def list_key_exist(key, env: list[str]):
    for item in env:
        if key in item:
            return item
    else:
        return None


def patch_service_set(dc_cfg: dict, services_map: dict[str, str]):
    new_dc_cfg = deepcopy(dc_cfg)
    for service in dc_cfg['services']:
        if service not in services_map:
            del new_dc_cfg['services'][service]
    return new_dc_cfg


def patch_envs(dc_cfg: dict, services_environment_vars: Environment):
    # TODO envs order and override question!!
    #  if we overrides env, should we save order? or insert before, for allow to override codegen
    new_dc_cfg = deepcopy(dc_cfg)
    for service in dc_cfg['services']:
        if 'environment' not in dc_cfg['services'][service]:
            new_dc_cfg['services'][service]['environment'] = []
        if isinstance(new_dc_cfg['services'][service]['environment'], list):
            for k, v in services_environment_vars[service].env.items():
                if existing := list_key_exist(f'{k}={v}',
                                              new_dc_cfg['services'][service]['environment']):
                    if existing != f'{k}={v}':
                        warn(
                            f'⚠️ env {k} for service {service} already set to "{existing}" '
                            f'instead of "{v}"')
                else:
                    new_dc_cfg['services'][service]['environment'] += [f'{k}={v}']
        elif isinstance(new_dc_cfg['services'][service]['environment'], dict):
            for k, v in services_environment_vars[service].env.items():
                if k in new_dc_cfg['services'][service]['environment']:
                    if new_dc_cfg['services'][service]['environment'][k] != v:
                        warn(f'⚠️ env {k} for service {service} already set to '
                             f"\"{new_dc_cfg['services'][service]['environment'][k]}\" instead "
                             f"of \"{v}\"")
                else:
                    new_dc_cfg['services'][service]['environment'].update({k: v})
    return new_dc_cfg


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


def patch_services_names(dc_cfg: dict, services_map: dict[str, str]) -> dict:
    new_service_dc_cfg = deepcopy(dc_cfg)
    new_service_dc_cfg['services'] = {}
    for service in dc_cfg['services']:
        srv_cfg = deepcopy(dc_cfg['services'][service])

        result_service_name = services_map[service]
        new_service_dc_cfg['services'][result_service_name] = srv_cfg

        if 'depends_on' in srv_cfg:
            if isinstance(srv_cfg['depends_on'], list):
                new_deps = [
                    services_map[item] for item in srv_cfg['depends_on']
                ]
                new_service_dc_cfg['services'][result_service_name] = srv_cfg | {
                    'depends_on': new_deps
                }
            if isinstance(srv_cfg['depends_on'], dict):
                new_deps = {
                    services_map[service_name]: condition
                    for service_name, condition in srv_cfg['depends_on'].items()
                }
                new_service_dc_cfg['services'][result_service_name] = srv_cfg | {
                    'depends_on': new_deps
                }
    return new_service_dc_cfg


def patch_docker_compose_file_services(filename: Path,
                                       host_root: Path,
                                       services_environment_vars: Environment,
                                       network_name: str, services_map: dict[
        str, str]):  # TODO network_name = [projectname]_default
    dc_cfg = read_dc_file(filename)

    dc_cfg = patch_network(dc_cfg, network_name=network_name)

    dc_cfg = patch_service_set(dc_cfg, services_map)  # todo use servcie_map

    dc_cfg = patch_envs(dc_cfg, services_environment_vars)  # todo use servcie_map

    dc_cfg = patch_services_names(dc_cfg, services_map)  # todo use servcie_map istead postfix

    dc_cfg = patch_services_volumes(dc_cfg, host_root)

    write_dc_file(filename, dc_cfg)


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
            services += list(dc_cfg['services'].keys())
    return services


def make_env_compose_instance_files(env_config_instance: EnvConfigInstance,
                                    compose_files: str,
                                    project_network_name: str,  # without "_default"
                                    host_project_root_directory,
                                    compose_files_path: Path = Path('/compose-files'),
                                    # dot_env_files_path: Path = Path('/docker-composes/envs'),
                                    tmp_env_path: Path = Path('/env-tmp'),
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

    return EnvConfigComposeInstance(
        env_config_instance=env_config_instance,
        compose_files_source=compose_files,
        directory=dst,
        compose_files=new_compose_files_list
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


def run_env(dc_env_config: EnvConfigComposeInstance, in_docker_project_root, except_containers: list[str]):
    services = list(dc_env_config.env_config_instance.env_services_map.values())
    CONSOLE.print(
        Text('Starting services: ', style=Style.info)
        .append(Text(str(services), style=Style.good))
    )
    if dc_env_config.env_config_instance.env_id == EMPTY_ID:
        for container in except_containers:
            if container in services:
                services.remove(container)
        print(f'Starting services except original e2e, dockersock already started: {services}')

    execution_envs = dict(os.environ)
    execution_envs['COMPOSE_FILE'] = dc_env_config.compose_files
    up = subprocess.call(
        ['docker-compose', '--project-directory', '.', 'up', '--timestamps', '--no-deps', '--pull', 'never', '--timeout', '300', '-d', *services],
        env=execution_envs,
        cwd=in_docker_project_root
    )
    if up != 0:
        print('Не смогли поднять')  # TODO make error type + dc down  or в diagnostic mode
        print_state(execution_envs, in_docker_project_root)
        sys.exit(up)

    # -> print how to connect and dc aliases

    # # TODO extract check into maxxwelld
    # check = subprocess.call(
    #     [
    #         'docker-compose', '--project-directory', '.', 'exec',
    #         dc_env_config.env_config_instance.env_services_map['e2e'],
    #         '/project/build/check-containers-started.sh'
    #     ],
    #     env=execution_envs,
    #     cwd=in_docker_project_root
    # )
    # assert check == 0, 'Не дождались поднятия всего'  # TODO make error type + dc down  or в
    # diagnostic mode -> print how to connect and dc aliaces

    # run after servoice and after all hooks
    # TODO move after service, after service up
    for current_stage in [EventStage.BEFORE_ALL, EventStage.BEFORE_SERVICE_START, EventStage.AFTER_SERVICE_START, EventStage.AFTER_ALL]:
        for service in dc_env_config.env_config_instance.env:
            for handler in dc_env_config.env_config_instance.env[service].events_handlers:
                if handler.stage != current_stage:
                    continue

                if isinstance(handler, FuncHandler):
                    handler.func()
                    continue

                if isinstance(handler, ComposeStateHandler):
                    get_services_state = partial(dc_state, env=execution_envs, root=in_docker_project_root)
                    # TODO migrate to non-0 return codes
                    # TODO unify interface args kwargs
                    res = handler.func(get_services_state, services)
                    if res != 0:
                        print(f'Не не получилось успешно обработать хук {handler}')
                        sys.exit(res)
                    continue

                target_service = dc_env_config.env_config_instance.env_services_map[
                    handler.executor or service
                ]

                substituted_cmd = []
                for cmd_part in handler.cmd:
                    if isinstance(cmd_part, AsIs):
                        substituted_cmd += [cmd_part.value]
                        continue
                    substituted_cmd += [
                        cmd_part.format(**dc_env_config.env_config_instance.env_services_map)
                    ]
                print(f'Executing in {target_service} container: {substituted_cmd}')
                hook = subprocess.call(
                    [
                        'docker-compose', '--project-directory', '.',
                        'exec', f'{target_service}', *substituted_cmd
                    ],
                    env=execution_envs,
                    cwd=in_docker_project_root
                )
                # TODO make error type + dc down  or в diagnostic mode -> print how to connect
                #  and dc aliaces
                if hook != 0:
                    print(f'Не не получилось успешно обработать хук {handler}')
                    print_state(execution_envs, in_docker_project_root)
                    sys.exit(hook)



# def down_env(dc_env_config: EnvConfigComposeInstance, in_docker_project_root):
#     services = list(dc_env_config.env_config_instance.env_services_map.values())
#     print(f'Down services: {services}')
#     if dc_env_config.env_config_instance.env_id == EMPTY_ID:
#         if 'e2e' in services:
#             services.remove('e2e')
#         if 'dockersock' in services:
#             services.remove('dockersock')
#         print(f'Down services except original e2e, dockersock started: {services}')
#
#     execution_envs = dict(os.environ)
#     execution_envs['COMPOSE_FILE'] = dc_env_config.compose_files
#     up = subprocess.call(
#         ['docker-compose', '--project-directory', '.', 'down', *services],
#         env=execution_envs,
#         cwd=in_docker_project_root
#     )
#     assert up == 0, 'Не смогли прибить все поднятое'  # TODO make error type + dc down  or в diagnostic mode


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
