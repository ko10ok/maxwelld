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
from maxwelld.server.handlers.dc_logs import DcLogsRequestParams
from schemas.http_codes import HTTPStatusCodeOk


class Scenario(vedro.Scenario):
    async def no_docker_containers(self):
        no_docker_containers()

    async def no_docker_copose_files(self):
        no_docker_compose_files()

    async def given_compose_files(self):
        compose_file(
            'docker-compose.yaml',
            content="""
version: "3"

services:
  s1:
    image: busybox:stable
    command: 'sh -c "echo this is log s1; trap : TERM INT; sleep 604800; wait"'
  
  s2:
    image: busybox:stable
    command: 'sh -c "echo this is log s2; trap : TERM INT; sleep 604800; wait"'
"""
        )

    async def given_no_params_for_env_to_up(self):
        self.started_services = await services_started(
            compose_files='docker-compose.yaml',
            environment=Environment(
                'DEFAULT',
                Service('s1'),
                Service('s2'),
            )
        )

    async def given_logs_params(self):
        self.logs_params: DcLogsRequestParams = {
            'env_id': self.started_services['env_id'],
            'services': ['s1', 's2'],
        }

    async def when_user_get_service_logs(self):
        self.response = await MaxwelldApi().logs(self.logs_params)

    async def then_it_should_return_successful_code(self):
        assert self.response.status_code == HTTPStatusCodeOk

    async def then_it_should_return_logs(self):
        assert self.response.json() == schema.dict({'logs': schema.str})

    async def and_it_should_contain_service_logs(self):
        self.logs = debase64_pickled(self.response.json()['logs'])
        assert self.logs == schema.dict({
            's1': schema.bytes % b'this is log s1\n',
            's2': schema.bytes % b'this is log s2\n',
        })
