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
from maxwelld import Environment
from maxwelld import Service
from maxwelld.helpers.bytes_pickle import base64_pickled
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
        self.compose_filename = 'docker-compose.basic.yaml'
        self.migration_result_file = '/tmp/migration.log'
        self.migration = {}
        self.services = ['s1', 's2']
        for service in self.services:
            self.migration[service] = fake(schema.str.len(1, 10))
        self.service_compose_content = """
version: "3"

services:
  s1:
    image: busybox:stable
    command: 'sh -c "trap : TERM INT; sleep 604800; wait"'
    x-migration: 
      - after_start: sh -c 'echo "s1 after_start" >> /tmp/migration.log'
      - after_all: sh -c 'echo "s1 after_all" >> /tmp/migration.log'

  s2:
    image: busybox:stable
    command: 'sh -c "trap : TERM INT; sleep 604800; wait"'
    x-migration: 
      - before_start: [ [sh -c 'echo "s2 before_start" >> /tmp/migration.log' ], s1 ]
      - after_start: [ [sh -c 'echo "s2 after_start" >> /tmp/migration.log' ], s1 ]
    depends_on:
      s1:
        condition: service_healthy
"""
        compose_file(
            self.compose_filename,
            content=self.service_compose_content
        )

    async def given_no_params_for_env_to_up(self):
        self.params: DcUpRequestParams = {
            'name': fake(EnvNameSchema),
            'compose_files': 'docker-compose.basic.yaml',
            'config_template': base64_pickled(
                Environment(
                    'DEFAULT',
                    Service('s1'),
                    Service('s2'),
                    Service('s3'),
                    Service('s4'),
                )
            ),
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
            ...,
            ContainerSchema % {
                'Labels': {
                    'com.docker.compose.service': 's1',
                    'com.docker.compose.project.config_files': f'/tmp-envs/no_id/{self.compose_filename}',
                },
            },
            ...,
        ])
        assert self.containers == schema.list([
            ...,
            ContainerSchema % {
                'Labels': {
                    'com.docker.compose.service': 's2',
                    'com.docker.compose.project.config_files': f'/tmp-envs/no_id/{self.compose_filename}',
                },
            },
            ...,
        ])

    @retry(attempts=3, delay=1)
    async def then_it_should_apply_s1_migration(self):
        self.migration_s1_file_content = get_file_from_container('s1', self.migration_result_file)
        assert self.migration_s1_file_content == schema.bytes % (b's1 after_start\n'
                                                                 b's2 before_start\n'
                                                                 b's2 after_start\n'
                                                                 b's1 after_all\n')

    @retry(attempts=3, delay=1)
    async def then_it_should_apply_s2_migration(self):
        self.migration_s2_file_content = get_file_from_container('s2', self.migration_result_file)
        assert self.migration_s2_file_content == schema.none
