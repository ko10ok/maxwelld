import asyncio
import traceback
from typing import TypedDict

from aiohttp import web
from aiohttp.web_request import Request

from maxwelld.client.types import EnvironmentId
from maxwelld.core.service import MaxwellDemonServiceManager
from maxwelld.errors.up import ServicesUpError
from maxwelld.helpers.bytes_pickle import debase64_pickled

UP_LOCK = asyncio.Lock()


class DcUpRequestParams(TypedDict):
    name: str | None
    config_template: str | None
    compose_files: str | None
    isolation: bool | None
    parallelism_limit: int | None
    force_restart: bool | None


DC_UP_DEFAULTS = {
    'name': 'DEFAULT_FULL',
    'config_template': None,
    'compose_files': None,
    'isolation': False,
    'parallelism_limit': 1,
    'force_restart': False,
}


class UpResponseParams(TypedDict):
    env_id: EnvironmentId


class UpErrorResponseParams(TypedDict):
    error: str


async def dc_up(request: Request) -> web.Response:
    params: DcUpRequestParams = DC_UP_DEFAULTS | await request.json()
    config_template = debase64_pickled(params['config_template']) if params['config_template'] else None

    # TODO move to up_or_get_existing
    # TODO kill existing composes??
    try:
        env_id, is_new = await MaxwellDemonServiceManager().get().up_or_get_existing(
            name=params['name'],
            config_template=config_template,
            compose_files=params['compose_files'],
            isolation=params['isolation'],
            parallelism_limit=params['parallelism_limit'],
            force_restart=params['force_restart'],
        )
    except ServicesUpError as e:
        return web.json_response(UpErrorResponseParams(error=e.message), status=422)
    except AssertionError as e:
        return web.json_response(UpErrorResponseParams(error=f'Somthing went wrong:\n{str(e)}'), status=422)
    except BaseException as e:
        return web.json_response(UpErrorResponseParams(error=f'Somthing went terribly wrong:\n{str(e)}\n\n{traceback.format_exc()}'), status=422)
    return web.json_response(UpResponseParams(env_id=env_id), status=200)
