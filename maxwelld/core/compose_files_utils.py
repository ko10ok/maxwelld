from _warnings import warn
from copy import deepcopy
from pathlib import Path

import yaml

from maxwelld import Environment


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
