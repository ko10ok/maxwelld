import pickle

import aiohttp

from maxwelld.client.types import EnvironmentId
from maxwelld.core.docker_compose_interface import ServicesComposeState
from maxwelld.core.service import MaxwellDemonService
from maxwelld.env_description.env_types import Environment
from maxwelld.helpers.bytes_pickle import base64_pickled
from maxwelld.server.commands import HEALTHCHECK
from maxwelld.server.commands import UP_PATH
from maxwelld.server.handlers.up import UpRequestParams
from maxwelld.server.handlers.up import UpResponseParams


class MaxwellDemonClient:
    def __init__(self, host, project, non_stop_containers, port=80):
        self._project = project
        self._non_stop_containers = non_stop_containers
        self._server = MaxwellDemonService(project, self._non_stop_containers)
        self._server_host = host
        self._server_port = port
        self._server_url = f'{self._server_host}:{self._server_port}'

    async def healthcheck(self):
        async with aiohttp.ClientSession() as session:
            url = f'{self._server_url}{HEALTHCHECK}'
            async with session.get(url) as response:
                assert response.status == 200, response
                state = await response.json()
                assert 'status' in state, response
                assert state['status'] == 'ok', response

    def up_compose(self, name, config_template: Environment, compose_files: str, isolation=None,
                   parallelism_limit=None, verbose=False) -> EnvironmentId:
        return self._server.up_compose(
            name, config_template, compose_files, isolation, parallelism_limit, verbose
        )

    async def up(self, name, config_template: Environment, compose_files: str, isolation=None,
                 parallelism_limit=None) -> EnvironmentId:
        url = f'{self._server_url}{UP_PATH}'
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=UpRequestParams(
                    name=name,
                    config_template=base64_pickled(config_template),
                    compose_files=compose_files,
                    isolation=isolation,
                    parallelism_limit=parallelism_limit,
                    non_stop_containers=self._non_stop_containers,
            )) as response:
                assert response.status == 200, response
                return UpResponseParams(**await response.json())['env_id']

    def env(self, env_id: EnvironmentId) -> Environment:
        env = self._server.env(env_id=env_id)
        return pickle.loads(env)

    def status(self, env_id: EnvironmentId) -> ServicesComposeState:
        status = self._server.status(env_id=env_id)
        return pickle.loads(status)

    def list_current_in_flight_envs(self, *args, **kwargs):
        raise NotImplementedError()

    def list_services(self, *args, **kwargs):
        raise NotImplementedError()

# class MaxwellDemonClient:
#     def __init__(self, server_host, project, non_stop_containers):
#         self._project = project
#         self._non_stop_containers = non_stop_containers
#         self._server_host = server_host
#
#     def _up(self, name, config_template, compose_files, isolation, parallelism_limit):
#         ...
#
#     def up_compose(self, name, config_template: Environment, compose_files: str, isolation=None,
#                    parallelism_limit=None, verbose=False) -> Environment:
#         return self._server.up_compose(
#             name, config_template, compose_files, isolation, parallelism_limit, verbose
#         )
#
#     def status(self, name):
#         ...
#
#     def list_current_in_flight_envs(self, *args, **kwargs):
#         raise NotImplementedError()
#
#     def list_services(self, *args, **kwargs):
#         raise NotImplementedError()
