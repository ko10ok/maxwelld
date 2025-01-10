from d42 import fake

from interfaces.maxwelld_api import MaxwelldApi
from maxwelld import Environment
from maxwelld.helpers.bytes_pickle import base64_pickled
from maxwelld.server.handlers.dc_up import DcUpRequestParams
from schemas.env_name import EnvNameSchema


async def services_started(compose_files: str, environment: Environment, env_name: str = None, headers: dict = None):
    if env_name is None:
        env_name = fake(EnvNameSchema)

    params: DcUpRequestParams = {
        'name': env_name,
        'compose_files': compose_files,
        'config_template': base64_pickled(environment),
        'parallelism_limit': 1,
        'isolation': False,
        'force_restart': False,
    }

    response = await MaxwelldApi().up(params, headers=headers)

    assert response.status_code == 200, response.text

    return response.json()
