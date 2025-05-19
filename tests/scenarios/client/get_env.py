from asyncio import sleep

import vedro
from d42 import fake
from d42 import from_native

from contexts.compose_file import compose_file
from contexts.no_docker_compose_files import no_docker_compose_files
from contexts.no_docker_containers import no_docker_containers
from contexts.services_started import services_started
from maxwelld import Environment
from maxwelld import MaxwellDemonClient
from maxwelld import Service
from schemas.service import ServiceNameSchema


class Scenario(vedro.Scenario):
    async def no_docker_containers(self):
        no_docker_containers()

    async def no_docker_copose_files(self):
        no_docker_compose_files()

    async def given_compose_files(self):
        self.service_name = fake(ServiceNameSchema)
        compose_file(
            'docker-compose.yaml',
            content=f"""
version: "3"

services:
  {self.service_name}:
    image: busybox:stable
    command: 'sh -c "trap : TERM INT; sleep 604800; wait"'
"""
        )
        compose_file(
            'docker-compose.dev.yaml',
            content="""
version: "3"

services:
  s2:
    image: busybox:stable
    command: 'sh -c "trap : TERM INT; sleep 604800; wait"'
"""
        )

    async def given_servicese_started(self):
        self.env = Environment(
            'DEFAULT',
            Service(self.service_name),
        )
        self.started_service = await services_started(
            compose_files='docker-compose.yaml:docker-compose.dev.yaml',
            environment=self.env
        )

    async def given_client(self):
        self.md_client = MaxwellDemonClient('http://maxwelld')

    async def wait_for_up(self):
        await sleep(5)

    async def when_user_gets_status(self):
        self.response = await self.md_client.env(env_id=self.started_service['env_id'])

    async def then_it_should_return_successful_code(self):
        assert isinstance(self.response, Environment)

    async def and_env_names_should_be_runninh(self):
        assert self.response == self.env

    async def and_env_internals_should_be_runninh(self):
        self.env_internals = self.response.as_json()
        assert self.env_internals == from_native(self.env.as_json())
