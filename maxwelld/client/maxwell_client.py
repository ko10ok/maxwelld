from maxwelld.core.service import MaxwellDemonService
from maxwelld.client.types import EnvironmentId
from maxwelld.env_description.env_types import Environment


class MaxwellDemonClient:
    def __init__(self, project, non_stop_containers):
        self._project = project
        self._non_stop_containers = non_stop_containers
        self._server = MaxwellDemonService(project, self._non_stop_containers)

    def up_compose(self, name, config_template: Environment, compose_files: str, isolation=None,
                   parallelism_limit=None, verbose=False) -> Environment:
        return self._server.up_compose(
            name, config_template, compose_files, isolation, parallelism_limit, verbose
        )

    def status(self, env_id: EnvironmentId, config_template: Environment) -> (Environment, list[dict]):
        env, status = self._server.status(env_id=env_id, config_template=config_template)
        return env, status

    def list_current_in_flight_envs(self, *args, **kwargs):
        raise NotImplementedError()

    def list_services(self, *args, **kwargs):
        raise NotImplementedError()

# class MaxwellDemonClient:
#     def __init__(self, server_host, project, non_stop_containers):
#         self._project = project
#         self._non_stop_containers = non_stop_containers
#         self._server_host = server_host
#
#     def _up(self, name, config_template, compose_files, isolation, parallelism_limit):
#         ...
#
#     def up_compose(self, name, config_template: Environment, compose_files: str, isolation=None,
#                    parallelism_limit=None, verbose=False) -> Environment:
#         return self._server.up_compose(
#             name, config_template, compose_files, isolation, parallelism_limit, verbose
#         )
#
#     def status(self, name):
#         ...
#
#     def list_current_in_flight_envs(self, *args, **kwargs):
#         raise NotImplementedError()
#
#     def list_services(self, *args, **kwargs):
#         raise NotImplementedError()
