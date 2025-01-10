import vedro
from d42 import fake
from d42 import schema

from contexts.compose_file import compose_file
from contexts.no_docker_compose_files import no_docker_compose_files
from contexts.no_docker_containers import no_docker_containers
from interfaces.maxwelld_api import MaxwelldApi
from maxwelld import Environment
from maxwelld import Service
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

    async def given_no_params_for_env_to_up(self):
        self.params: DcUpRequestParams = {
            'name': fake(EnvNameSchema),
            'compose_files': 'docker-compose.dev.yaml',
            'config_template': base64_pickled(
                Environment(
                    'DEFAULT',
                    Service('s2')
                )
            ),
            'parallelism_limit': 1,
            'isolation': False,
            'force_restart': False,
        }

    async def when_user_up_env_without_params(self):
        self.response = await MaxwelldApi().up(self.params)

    async def then_it_should_return_successful_code(self):
        assert self.response.status_code == HTTPStatusUnprocessableEntity

    async def then_it_should_out_services_logs(self):
        self.response_json = self.response.json()
        assert self.response_json == schema.dict({'error': schema.str})
        assert 'error service exception log' in self.response_json['error']
