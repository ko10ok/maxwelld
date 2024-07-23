import aiohttp
from aiohttp import ClientConnectorError
from rtry import retry

from maxwelld.client.types import EnvironmentId
from maxwelld.core.compose_data_types import ServicesComposeState
from maxwelld.errors.up import ServicesUpError
from maxwelld.env_description.env_types import Environment
from maxwelld.helpers.bytes_pickle import base64_pickled
from maxwelld.helpers.bytes_pickle import debase64_pickled
from maxwelld.server.commands import DC_EXEC_PATH
from maxwelld.server.commands import DC_LOGS_PATH
from maxwelld.server.commands import DC_UP_PATH
from maxwelld.server.commands import ENV_PATH
from maxwelld.server.commands import HEALTHCHECK_PATH
from maxwelld.server.commands import STATUS_PATH
from maxwelld.server.handlers.dc_exec import DcExecRequestParams
from maxwelld.server.handlers.dc_exec import DcExecResponseParams
from maxwelld.server.handlers.dc_logs import DcLogsRequestParams
from maxwelld.server.handlers.env import EnvRequestParams
from maxwelld.server.handlers.env import EnvResponseParams
from maxwelld.server.handlers.status import StatusResponseParams
from maxwelld.server.handlers.up import UpRequestParams
from maxwelld.server.handlers.up import UpResponseParams


class MaxwellDemonClient:
    def __init__(self, host, port=80):
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

    @retry(attempts=10, delay=1, swallow=ClientConnectorError)
    async def up(self, name, config_template: Environment, compose_files: str, isolation=None,
                 parallelism_limit=None, force_restart: bool = False) -> EnvironmentId:
        url = f'{self._server_url}{DC_UP_PATH}'
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=UpRequestParams(
                name=name,
                config_template=base64_pickled(config_template),
                compose_files=compose_files,
                isolation=isolation,
                parallelism_limit=parallelism_limit,
                force_restart=force_restart,
            )) as response:
                if response.status == 422:
                    raise ServicesUpError((await response.json())['error'])
                if response.status == 500:
                    raise ServicesUpError((await response.json())['error'])
                assert response.status == 200, response
                response_body = UpResponseParams(**await response.json())
                return response_body['env_id']

    @retry(attempts=5, delay=1, swallow=Exception)
    async def env(self, env_id: EnvironmentId) -> Environment:
        url = f'{self._server_url}{ENV_PATH}'
        async with aiohttp.ClientSession() as session:
            async with session.get(url, json=EnvRequestParams(id=env_id)) as response:
                assert response.status == 200, response
                response_body = EnvResponseParams(**await response.json())
                return debase64_pickled(response_body['env'])

    @retry(attempts=5, delay=1, swallow=Exception)
    async def status(self, env_id: EnvironmentId) -> ServicesComposeState:
        url = f'{self._server_url}{STATUS_PATH}'
        async with aiohttp.ClientSession() as session:
            async with session.get(url, json=EnvRequestParams(id=env_id)) as response:
                assert response.status == 200, response
                response_body = StatusResponseParams(**await response.json())
                return debase64_pickled(response_body['status'])

    async def exec(self, env_id: EnvironmentId, container: str, command: str) -> ServicesComposeState:
        url = f'{self._server_url}{DC_EXEC_PATH}'
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=DcExecRequestParams(
                env_id=env_id,
                container=container,
                command=command
            )) as response:
                assert response.status == 200, response
                response_body = DcExecResponseParams(**await response.json())
                return debase64_pickled(response_body['output'])

    async def logs(self, env_id: EnvironmentId, services: list[str]) -> dict[str, bytes]:
        url = f'{self._server_url}{DC_LOGS_PATH}'
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=DcLogsRequestParams(
                env_id=env_id,
                services=services,
            )) as response:
                assert response.status == 200, response
                response_body = DcExecResponseParams(**await response.json())
                return debase64_pickled(response_body['logs'])

    def list_current_in_flight_envs(self, *args, **kwargs):
        raise NotImplementedError()

    def list_services(self, *args, **kwargs):
        raise NotImplementedError()
