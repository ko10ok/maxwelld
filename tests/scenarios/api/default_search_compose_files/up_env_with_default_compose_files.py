import vedro
from d42 import fake
from d42 import schema
from rtry import retry

from contexts.compose_file import cleanup_compose_files
from contexts.compose_file import compose_file
from contexts.no_docker_compose_files import no_docker_compose_files
from contexts.no_docker_containers import no_docker_containers
from contexts.no_docker_containers import retrieve_all_docker_containers
from helpers.docker_migration_result import get_file_from_container
from interfaces.maxwelld_api import MaxwelldApi
from libs.env_const import SYSTEM_DEFAULT_FULL
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
        self.compose_filename_1 = 'docker-compose.yaml'
        compose_file(
            self.compose_filename_1,
            content="""
version: "3"

services:
  s1:
    image: busybox:stable
    command: 'sh -c "trap : TERM INT; sleep 604800; wait"'
"""
        )
        self.compose_filename_2 = 'tests/e2e/docker-compose.yaml'
        compose_file(
            self.compose_filename_2,
            content="""
version: "3"

services:
  s2:
    image: busybox:stable
    command: 'sh -c "trap : TERM INT; sleep 604800; wait"'
"""
        )
        self.compose_filename_3 = 'tests/e2e/unreachable/docker-compose.yaml'
        compose_file(
            self.compose_filename_3,
            content="""
version: "3"

services:
  s3:
    image: busybox:stable
    command: 'sh -c "trap : TERM INT; sleep 604800; wait"'
"""
        )

    async def given_no_params_for_env_to_up(self):
        self.env_name = fake(EnvNameSchema)
        self.params: DcUpRequestParams = {
            'name': self.env_name,
            'compose_files': None,
            'config_template': None,
            'parallelism_limit': 1,
            'isolation': False,
            'force_restart': False,
        }

    async def when_user_up_env_without_params(self):
        self.response = await MaxwelldApi().up(self.params)

    async def then_it_should_return_successful_code(self):
        assert self.response.status_code == HTTPStatusCodeOk

    async def then_it_should_up_default_env_service(self):
        self.containers = retrieve_all_docker_containers()
        assert self.containers == schema.list([
            ...,
            ContainerSchema % {
                'Labels': {
                    'com.docker.compose.service': 'default-config-service',
                    'com.docker.compose.project.config_files':
                        f'/tmp-envs/no_id/{self.compose_filename_1}'
                        f',/tmp-envs/no_id/docker-compose.default.yaml'
                        f',/tmp-envs/no_id/{self.compose_filename_2.replace("/", "-")}',

                    Label.ENV_ID: 'no_id',
                    Label.REQUEST_ENV_NAME: self.env_name,
                    Label.CLIENT_ENV_NAME: SYSTEM_DEFAULT_FULL,

                    Label.COMPOSE_FILES: f'{self.compose_filename_1}'
                                         f':docker-compose.default.yaml'
                                         f':{self.compose_filename_2}',
                    Label.COMPOSE_FILES_INSTANCE:
                        f'/tmp-envs/no_id/{self.compose_filename_1}'
                        f':/tmp-envs/no_id/docker-compose.default.yaml'
                        f':/tmp-envs/no_id/{self.compose_filename_2.replace("/", "-")}',
                },
            },
            ...,
        ])

    async def and_it_should_up_s1_env_service(self):
        self.containers = retrieve_all_docker_containers()
        assert self.containers == schema.list([
            ...,
            ContainerSchema % {
                'Labels': {
                    'com.docker.compose.service': 's1',
                    'com.docker.compose.project.config_files':
                        f'/tmp-envs/no_id/{self.compose_filename_1}'
                        f',/tmp-envs/no_id/docker-compose.default.yaml'
                        f',/tmp-envs/no_id/{self.compose_filename_2.replace("/", "-")}',

                    Label.ENV_ID: 'no_id',
                    Label.REQUEST_ENV_NAME: self.env_name,
                    Label.CLIENT_ENV_NAME: SYSTEM_DEFAULT_FULL,

                    Label.COMPOSE_FILES: f'{self.compose_filename_1}'
                                         f':docker-compose.default.yaml'
                                         f':{self.compose_filename_2}',
                    Label.COMPOSE_FILES_INSTANCE:
                        f'/tmp-envs/no_id/{self.compose_filename_1}'
                        f':/tmp-envs/no_id/docker-compose.default.yaml'
                        f':/tmp-envs/no_id/{self.compose_filename_2.replace("/", "-")}',
                },
            },
            ...,
        ])

    async def and_it_should_up_s2_env_service(self):
        self.containers = retrieve_all_docker_containers()
        assert self.containers == schema.list([
            ...,
            ContainerSchema % {
                'Labels': {
                    'com.docker.compose.service': 's2',
                    'com.docker.compose.project.config_files':
                        f'/tmp-envs/no_id/{self.compose_filename_1}'
                        f',/tmp-envs/no_id/docker-compose.default.yaml'
                        f',/tmp-envs/no_id/{self.compose_filename_2.replace("/", "-")}',

                    Label.ENV_ID: 'no_id',
                    Label.REQUEST_ENV_NAME: self.env_name,
                    Label.CLIENT_ENV_NAME: SYSTEM_DEFAULT_FULL,

                    Label.COMPOSE_FILES: f'{self.compose_filename_1}'
                                         f':docker-compose.default.yaml'
                                         f':{self.compose_filename_2}',
                    Label.COMPOSE_FILES_INSTANCE:
                        f'/tmp-envs/no_id/{self.compose_filename_1}'
                        f':/tmp-envs/no_id/docker-compose.default.yaml'
                        f':/tmp-envs/no_id/{self.compose_filename_2.replace("/", "-")}',
                },
            },
            ...,
        ])
