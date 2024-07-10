import collections
import shutil
import sys
from _warnings import warn
from copy import deepcopy
from pathlib import Path

import yaml

from maxwelld.core.sequence_run_types import ComposeInstanceFiles
from maxwelld.core.sequence_run_types import EnvInstanceConfig
from maxwelld.core.utils.compose_instance_cfg import get_new_instance_compose_files
from maxwelld.env_description.env_types import Environment
from maxwelld.env_description.env_types import EventStage
from maxwelld.env_description.env_types import Handler


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
    # new_dc_cfg['networks']['e2e_back_network'] = {
    #     'name': network_name,
    #     'external': True,
    # }

    for service in new_dc_cfg['services']:
        if 'network' not in new_dc_cfg['services'][service]:
            new_dc_cfg['services'][service]['networks'] = []
        # new_dc_cfg['services'][service]['networks'] += ['e2e_back_network']
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


def list_key_exist(key, env: list[str]) -> None | str:
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
        if isinstance(new_dc_cfg['services'][service]['environment'], list) and service in services_environment_vars:
            for k, v in services_environment_vars[service].env.items():
                if existing := list_key_exist(f'{k}={v}',
                                              new_dc_cfg['services'][service]['environment']):
                    if existing != f'{k}={v}':
                        warn(
                            f'⚠️ env {k} for service {service} already set to "{existing}" '
                            f'instead of "{v}"')
                else:
                    new_dc_cfg['services'][service]['environment'] += [f'{k}={v}']
        elif isinstance(new_dc_cfg['services'][service]['environment'], dict) and service in services_environment_vars:
            for k, v in services_environment_vars[service].env.items():
                if k in new_dc_cfg['services'][service]['environment']:
                    if new_dc_cfg['services'][service]['environment'][k] != v:
                        warn(f'⚠️ env {k} for service {service} already set to '
                             f"\"{new_dc_cfg['services'][service]['environment'][k]}\" instead "
                             f"of \"{v}\"")
                else:
                    new_dc_cfg['services'][service]['environment'].update({k: v})
    return new_dc_cfg


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
                                       network_name: str,
                                       # TODO network_name = [projectname]_default
                                       services_map: dict[str, str] | None) -> None:
    dc_cfg = read_dc_file(filename)

    dc_cfg = patch_network(dc_cfg, network_name=network_name)

    if services_map:
        dc_cfg = patch_service_set(dc_cfg, services_map)  # todo use servcie_map

    if services_environment_vars:
        dc_cfg = patch_envs(dc_cfg, services_environment_vars)  # todo use servcie_map

    if services_map:
        dc_cfg = patch_services_names(dc_cfg, services_map)  # todo use servcie_map istead postfix

    dc_cfg = patch_services_volumes(dc_cfg, host_root)

    write_dc_file(filename, dc_cfg)


def parse_migration(migration: dict) -> Handler:
    assert isinstance(migration, dict), f'{migration} should be "stage: command" entry'
    assert len(migration) == 1, f'{migration} should have only one "stage: command" entry'
    assert list(migration.keys())[
               0] in EventStage.get_all_compose_stages(), (f"{migration} stage should only be one of "
                                                           f"{EventStage.get_all_compose_stages()}")

    for stage, command in migration.items():
        if isinstance(command, str):
            return Handler(
                EventStage.get_compose_stage(stage),
                cmd=command
            )

        if isinstance(command, list):
            assert len(command) >= 1, f"Migration {migration} command should have at least one command part"
            if isinstance(command[0], list):
                return Handler(
                    EventStage.get_compose_stage(stage),
                    cmd=' '.join(command[0]),
                    executor=command[1]
                )
            return Handler(
                EventStage.get_compose_stage(stage),
                cmd=' '.join(command)
            )

        if isinstance(command, dict):
            assert 'cmd' in command, f'migration {migration} should have "cmd" key to exec'
            assert 'executor' in command[0], f'migration {migration} should have "executor" key for target container'
            return Handler(
                EventStage.AFTER_SERVICE_START,
                cmd=command['cmd'],
                executor=command['executor']
            )

        assert False, (f'migration {command[0]} should have one of:\n'
                       f'x-migration:\n'
                       f'  - stage: command\n'
                       f'  - stage: [ command, cmd_part ]\n'
                       '  - stage: [ [command, cmd_part], executor ]\n'
                       '  - stage: { cmd: command, executor: executor_container_name}\n'
                       f'  - stage:\n'
                       f'      cmd: command\n'
                       f'      executor: executor_container_name\n'
                       f'formats')


def parse_migrations(migrations: list[dict]) -> list[Handler]:
    assert isinstance(migrations, list), (f'{migrations} should be list '
                                          f'of {{stage: [cmd, params]}}')
    result_hooks = []
    for migration in migrations:
        result_hooks += [parse_migration(migration)]
    return result_hooks


def extract_services_inline_migration(compose_files: list[str]) -> dict[str, list[str]]:
    migrations = collections.defaultdict(lambda: [])
    for filename in compose_files:
        dc_cfg = read_dc_file(filename)
        if 'services' in dc_cfg:
            for service in dc_cfg['services']:
                if service not in migrations:
                    migrations[service] = []

                if 'x-migration' in dc_cfg['services'][service]:
                    migrations[service] += parse_migrations(
                        dc_cfg['services'][service]['x-migration']
                    )

                assert 'x-migrate' not in dc_cfg['services'][
                    service], f'{service} have "x-migrate", do u mean "x-migration" section?'
                assert 'x-migrations' not in dc_cfg['services'][
                    service], f'{service} have "x-migrations", do u mean "x-migration" section?'

    return migrations


def make_env_compose_instance_files(env_config_instance: EnvInstanceConfig,
                                    compose_files: str,
                                    project_network_name: str,  # without "_default"
                                    host_project_root_directory,
                                    compose_files_path: Path,
                                    tmp_env_path: Path,
                                    ) -> ComposeInstanceFiles:
    dst = tmp_env_path / env_config_instance.env_id
    dst.mkdir(parents=True, exist_ok=True)

    for file in compose_files.split(':'):
        src_file = compose_files_path / file
        dst_file = dst / file
        shutil.copy(src_file, dst_file)

        print(env_config_instance)
        print(env_config_instance.env)  # Enviroment()
        print(env_config_instance.env_services_map)  # None
        sys.stdout.flush()

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

    return ComposeInstanceFiles(
        env_config_instance=env_config_instance,
        compose_files_source=compose_files,
        directory=dst,
        compose_files=new_compose_files_list,
        inline_migrations=inline_migrations,
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
