import vedro
from d42 import fake
from d42 import schema
from vedro import catched

from contexts.compose_file import compose_file
from contexts.no_docker_compose_files import no_docker_compose_files
from contexts.no_docker_containers import no_docker_containers
from interfaces.maxwelld_api import MaxwelldApi
from maxwelld import Environment
from maxwelld import MaxwellDemonClient
from maxwelld import Service
from maxwelld.core.errors import ServicesUpError
from maxwelld.helpers.bytes_pickle import base64_pickled
from maxwelld.server.handlers.dc_up import DcUpRequestParams
from schemas.env_name import EnvNameSchema
from schemas.http_codes import HTTPStatusUnprocessableEntity


class Scenario(vedro.Scenario):
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
    command: 'sh -c "echo error service exception log && sleep 5000 && echo `date +%s` > /tmp/healthcheck; trap : TERM INT; sleep 604800; wait"'
    healthcheck:
      test: ["CMD", "sh", "-c", "[ -f /tmp/healthcheck ] || exit 1"]
      interval: 5s
      timeout: 10s
      retries: 100
"""
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
        assert 'error service exception log' in str(self.exception.value)
