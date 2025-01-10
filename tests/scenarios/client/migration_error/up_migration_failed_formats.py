import vedro
from d42 import fake

from maxwelld.errors.up import ServicesUpError
from vedro import catched

from contexts.compose_file import compose_file
from contexts.no_docker_compose_files import no_docker_compose_files
from contexts.no_docker_containers import no_docker_containers
from maxwelld import Environment
from maxwelld import MaxwellDemonClient
from maxwelld import Service
from schemas.env_name import EnvNameSchema


class Scenario(vedro.Scenario):
    subject = 'up migration with wrong format with: \n{migrations}'

    @vedro.params(
        """
    x-migrations:
      - after_start: echo 1
    """.strip('\n'), """have similar to migrations key, do u mean "x-migration" section?"""
    )
    @vedro.params(
        """
    x-migrate:
      - after_start: echo 1
    """.strip('\n'), """have similar to migrations key, do u mean "x-migration" section?"""
    )
    @vedro.params(
        """
    x-migration:
      after_start: echo 1
    """.strip('\n'), """should match format:\nservice:\n  x-migration:\n    - stage: command"""
    )
    @vedro.params(
        """
    x-migration:
      - blahblah: echo 1
    """.strip('\n'), """stage should only be one of ['before_all', 'before_start', 'after_start', 'after_healthy', 'after_all']"""
    )
    def __init__(self, migrations, expected_error):
        self.migrations = migrations
        self.expected_error = expected_error

    async def no_docker_containers(self):
        no_docker_containers()

    async def no_docker_copose_files(self):
        no_docker_compose_files()

    async def given_compose_files(self):
        compose_file(
            'docker-compose.dev.yaml',
            content="""
version: "3"

services:
  s2:
    image: busybox:stable
    command: 'sh -c "trap : TERM INT; sleep 604800; wait"' 
""" + self.migrations
        )

    async def given_client(self):
        self.md_client = MaxwellDemonClient('http://maxwelld')

    async def when_user_up_env_without_params(self):
        with catched(Exception) as self.exception:
            self.response = await self.md_client.up(
                name=fake(EnvNameSchema),
                config_template=Environment(
                    'DEFAULT',
                    Service('s2')

                ),
                compose_files='docker-compose.dev.yaml',
                parallelism_limit=1,
            )

    async def then_it_should_throw_an_error(self):
        assert self.exception.type is ServicesUpError

    async def then_it_should_out_services_logs(self):
        assert '"s2"' in str(self.exception.value)
        assert self.expected_error in str(self.exception.value)
