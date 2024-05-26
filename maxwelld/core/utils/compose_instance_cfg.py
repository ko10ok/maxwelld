from pathlib import Path
from uuid import uuid4

from maxwelld import Env
from maxwelld import Environment
from maxwelld import Service
from maxwelld.client.types import EnvironmentId
from maxwelld.core.sequence_run_types import EMPTY_ID
from maxwelld.core.sequence_run_types import EnvInstanceConfig
from maxwelld.core.utils.compose_files import read_dc_file
from maxwelld.env_description.env_types import ServiceMode


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


def make_env_instance_config(env_template: Environment, env_id) -> EnvInstanceConfig:
    services_map = get_service_map(env_template, env_id)
    return EnvInstanceConfig(
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
