from d42 import fake

from interfaces.maxwelld_api import MaxwelldApi
from maxwelld import Environment
from maxwelld.helpers.bytes_pickle import base64_pickled
from maxwelld.server.handlers.dc_up import DcUpRequestParams
from schemas.env_name import EnvNameSchema
from schemas.http_codes import HTTPStatusCodeOk


async def services_started(compose_files: str, environment: Environment):
    params: DcUpRequestParams = {
        'name': fake(EnvNameSchema),
        'compose_files': compose_files,
        'config_template': base64_pickled(environment),
        'parallelism_limit': 1,
        'isolation': False,
        'force_restart': False,
    }

    response = await MaxwelldApi().up(params)

    assert response.status_code == HTTPStatusCodeOk

    return response.json()
