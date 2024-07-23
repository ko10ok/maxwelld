import vedro
from d42 import fake
from d42 import schema

from contexts.compose_file import compose_file
from contexts.no_docker_compose_files import no_docker_compose_files
from contexts.no_docker_containers import no_docker_containers
from contexts.no_docker_containers import retrieve_all_docker_containers
from interfaces.maxwelld_api import MaxwelldApi
from maxwelld import Environment
from maxwelld import Service
from maxwelld.helpers.bytes_pickle import base64_pickled
from maxwelld.server.handlers.dc_up import DcUpRequestParams
from schemas.docker import ContainerSchema
from schemas.env_name import EnvNameSchema
from schemas.http_codes import HTTPStatusCodeOk
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
    command: 'sh -c "trap : TERM INT; sleep 604800; wait"'
    x-migration:
        - after_start: echo 1
    - after_start: echo 1
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
        self.started_error = await MaxwelldApi().up(self.params)

    async def given_next_compose_files(self):
        compose_file(
            'docker-compose.dev.yaml',
            content="""
    version: "3"

    services:
      s2:
        image: busybox:stable
        command: 'sh -c "trap : TERM INT; sleep 604800; wait"'
        x-migration:
          - after_start: echo 1
    """
        )

    async def when_user_up_env_without_params(self):
        self.response = await MaxwelldApi().up(self.params)

    async def then_it_should_return_successful_code(self):
        self.response_text = self.response.text
        assert self.response.status_code == HTTPStatusCodeOk

    async def then_it_should_up_entire_env(self):
        self.containers = retrieve_all_docker_containers()
        assert self.containers == schema.list([
            ContainerSchema % {
                'Labels': {
                    'com.docker.compose.service': 's2',
                    'com.docker.compose.project.config_files': '/tmp-envs/no_id/docker-compose.dev.yaml',
                },
            },
        ])
