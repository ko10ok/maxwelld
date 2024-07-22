import vedro
from d42 import schema

from contexts.compose_file import compose_file
from contexts.no_docker_compose_files import no_docker_compose_files
from contexts.no_docker_containers import no_docker_containers
from contexts.services_started import services_started
from maxwelld import Environment
from maxwelld import MaxwellDemonClient
from maxwelld import Service


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
    command: 'sh -c "echo this is log; trap : TERM INT; sleep 604800; wait"'
"""
        )

    async def given_no_params_for_env_to_up(self):
        self.started_service = await services_started(
            compose_files='docker-compose.yaml',
            environment=Environment(
                'DEFAULT',
                Service('s1'),
            )
        )

    async def given_client(self):
        self.md_client = MaxwellDemonClient('http://maxwelld')

    async def when_user_gets_status(self):
        self.response = await self.md_client.logs(env_id=self.started_service['env_id'], services=['s1'])

    async def then_it_should_return_logs(self):
        assert self.response == schema.dict({'s1': schema.bytes % b'this is log\n'})
