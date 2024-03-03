import aiohttp
from rtry import retry

from maxwelld.client.types import EnvironmentId
from maxwelld.core.docker_compose_interface import ServicesComposeState
from maxwelld.core.service import MaxwellDemonService
from maxwelld.env_description.env_types import Environment
from maxwelld.helpers.bytes_pickle import base64_pickled
from maxwelld.helpers.bytes_pickle import debase64_pickled
from maxwelld.server.commands import ENV_PATH
from maxwelld.server.commands import HEALTHCHECK_PATH
from maxwelld.server.commands import STATUS_PATH
from maxwelld.server.commands import UP_PATH
from maxwelld.server.handlers.env import EnvRequestParams
from maxwelld.server.handlers.env import EnvResponseParams
from maxwelld.server.handlers.status import StatusResponseParams
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
            url = f'{self._server_url}{HEALTHCHECK_PATH}'
            async with session.get(url) as response:
                assert response.status == 200, response
                state = await response.json()
                assert 'status' in state, response
                assert state['status'] == 'ok', response

    @retry(attempts=5, delay=0.5, swallow=Exception)
    async def up(self, name, config_template: Environment, compose_files: str, isolation=None,
                 parallelism_limit=None) -> tuple[EnvironmentId, bool]:
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
                response_body = UpResponseParams(**await response.json())
                return response_body['env_id'], response_body['new']

    @retry(attempts=5, delay=0.5, swallow=Exception)
    async def env(self, env_id: EnvironmentId) -> Environment:
        url = f'{self._server_url}{ENV_PATH}'
        async with aiohttp.ClientSession() as session:
            async with session.get(url, json=EnvRequestParams(id=env_id)) as response:
                assert response.status == 200, response
                response_body = EnvResponseParams(**await response.json())
                return debase64_pickled(response_body['env'])

    @retry(attempts=5, delay=0.5, swallow=Exception)
    async def status(self, env_id: EnvironmentId) -> ServicesComposeState:
        url = f'{self._server_url}{STATUS_PATH}'
        async with aiohttp.ClientSession() as session:
            async with session.get(url, json=EnvRequestParams(id=env_id)) as response:
                assert response.status == 200, response
                response_body = StatusResponseParams(**await response.json())
                return debase64_pickled(response_body['status'])

    def list_current_in_flight_envs(self, *args, **kwargs):
        raise NotImplementedError()

    def list_services(self, *args, **kwargs):
        raise NotImplementedError()
