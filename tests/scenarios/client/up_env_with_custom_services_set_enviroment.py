import vedro
from d42 import fake
from d42 import schema

from contexts.compose_file import compose_file
from contexts.no_docker_compose_files import no_docker_compose_files
from contexts.no_docker_containers import no_docker_containers
from contexts.no_docker_containers import retrieve_all_docker_containers
from maxwelld import Environment
from maxwelld import MaxwellDemonClient
from maxwelld import Service
from schemas.docker import ContainerSchema
from schemas.env_name import EnvNameSchema
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

    async def given_client(self):
        self.md_client = MaxwellDemonClient('http://maxwelld')

    async def when_user_up_env_without_params(self):
        self.response = await self.md_client.up(
            name=fake(EnvNameSchema),
            config_template=Environment(
                'DEFAULT',
                Service('s2')

            ),
            compose_files='docker-compose.yaml:docker-compose.dev.yaml',
            parallelism_limit=1,
        )

    async def then_it_should_return_successful_code(self):
        assert self.response == schema.str

    async def then_it_should_up_entire_env(self):
        self.containers = retrieve_all_docker_containers()
        assert self.containers == schema.list([
            ContainerSchema % {
                'Labels': {
                    'com.docker.compose.service': 's2',
                    'com.docker.compose.project.config_files':
                        '/tmp-envs/no_id/docker-compose.yaml,/tmp-envs/no_id/docker-compose.dev.yaml',
                },
            },
        ])
