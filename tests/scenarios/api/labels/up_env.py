import vedro
from d42 import fake
from d42 import schema
from rtry import retry

from contexts.compose_file import compose_file
from contexts.no_docker_compose_files import no_docker_compose_files
from contexts.no_docker_containers import no_docker_containers
from contexts.no_docker_containers import retrieve_all_docker_containers
from helpers.docker_migration_result import get_file_from_container
from interfaces.maxwelld_api import MaxwelldApi
from maxwelld import DEFAULT_ENV
from maxwelld import Environment
from maxwelld import Service
from maxwelld.helpers.bytes_pickle import base64_pickled
from maxwelld.helpers.labels import Label
from maxwelld.server.handlers.dc_up import DcUpRequestParams
from schemas.docker import ContainerSchema
from schemas.env_name import EnvNameSchema
from schemas.http_codes import HTTPStatusCodeOk


class Scenario(vedro.Scenario):
    async def no_docker_containers(self):
        no_docker_containers()

    async def no_docker_copose_files(self):
        no_docker_compose_files()

    async def given_compose_file_with_service_with_migration(self):
        self.compose_filename = 'docker-compose.yaml'
        compose_file(
            self.compose_filename,
            content="""
version: "3"

services:
  s1:
    image: busybox:stable
    command: 'sh -c "trap : TERM INT; sleep 604800; wait"'
"""
        )

    async def given_no_params_for_env_to_up(self):
        self.env_name = fake(EnvNameSchema)
        self.client_env_name = 'DEF_BLA'
        self.config_template = base64_pickled(
            Environment(
                self.client_env_name,
                Service('s1'),
            )
        )
        self.params: DcUpRequestParams = {
            'name': self.env_name,
            'compose_files': self.compose_filename,
            'config_template': self.config_template,
            'parallelism_limit': 1,
            'isolation': False,
            'force_restart': False,
        }

    async def when_user_up_env_without_params(self):
        self.response = await MaxwelldApi().up(self.params)

    async def then_it_should_return_successful_code(self):
        assert self.response.status_code == HTTPStatusCodeOk

    async def then_it_should_up_entire_env(self):
        self.containers = retrieve_all_docker_containers()
        assert self.containers == schema.list([
            ContainerSchema % {
                'Labels': {
                    'com.docker.compose.service': 's1',
                    'com.docker.compose.project.config_files': f'/tmp-envs/no_id/{self.compose_filename}',

                    Label.ENV_ID: 'no_id',
                    Label.REQUEST_ENV_NAME: self.env_name,
                    Label.CLIENT_ENV_NAME: self.client_env_name,

                    Label.COMPOSE_FILES: f'{self.compose_filename}',
                    Label.COMPOSE_FILES_INSTANCE: f'/tmp-envs/no_id/{self.compose_filename}',

                    # 'com.maxwelld.env_config_template': self.config_template,
                    # 'com.maxwelld.env_service_map': '{"s1": "s1"}',

                    # 'com.maxwelld.env_params': '{}',
                },
            },
        ])
