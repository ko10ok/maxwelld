import vedro
from d42 import schema

from contexts.compose_file import compose_file
from contexts.no_docker_compose_files import no_docker_compose_files
from contexts.no_docker_containers import no_docker_containers
from contexts.services_started import services_started
from interfaces.maxwelld_api import MaxwelldApi
from maxwelld import Environment
from maxwelld import Service
from maxwelld.helpers.bytes_pickle import debase64_pickled
from maxwelld.server.handlers.dc_exec import DcExecRequestParams
from maxwelld.server.handlers.dc_exec_logs import DcExecLogsRequestParams
from schemas.http_codes import HTTPStatusCodeOk


@vedro.skip(reason='d-in-d container collapsed after exec?')
class Scenario(vedro.Scenario):
    async def no_docker_containers(self):
        no_docker_containers()

    async def no_docker_copose_files(self):
        no_docker_compose_files()

    async def given_compose_files(self):
        self.compose_filename = compose_file(
            'docker-compose.yaml',
            content="""
version: "3"

services:
  s1:
    image: busybox:stable
    command: 'sh -c "trap : TERM INT; sleep 604800; wait"'
"""
        )

    async def given_service_started(self):
        self.started_services = await services_started(
            self.compose_filename,
            Environment(
                'DEFAULT',
                Service('s1')
            )
        )

    async def given_execution_params(self):
        self.params = DcExecRequestParams(
            env_id=self.started_services['env_id'],
            container='s1',
            command='echo "Hello, World!"',
            detached=True,
        )


    async def given_executed_command(self):
        self.response = await MaxwelldApi().exec(self.params)
        self.uid = self.response.json()['uid']
        input()

    async def given_execution_get_logs_params(self):
        self.get_logs_params = DcExecLogsRequestParams(
            env_id=self.started_services['env_id'],
            container='s1',
            uid=self.started_services['env_id'],
        )

    async def when_user_exec_service_cmd(self):
        self.response = await MaxwelldApi().get_exec_logs(self.get_logs_params)

    async def then_it_should_return_successful_code(self):
        assert self.response.status_code == HTTPStatusCodeOk

    async def then_it_should_get_logs(self):
        assert self.response.json() == schema.dict({'output': schema.str})
        assert debase64_pickled(self.response.json()['output']) == schema.bytes(b'Hello, World!\n')
