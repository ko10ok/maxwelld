import asyncio
from typing import TypedDict

from aiohttp import web
from aiohttp.web_request import Request

from maxwelld.client.types import EnvironmentId
from maxwelld.core.service import MaxwellDemonServiceManager
from maxwelld.helpers.bytes_pickle import base64_pickled

UP_LOCK = asyncio.Lock()


class EnvRequestParams(TypedDict):
    id: EnvironmentId


class EnvResponseParams(TypedDict):
    env: str


async def http_get_env(request: Request) -> web.Response:
    params: EnvRequestParams = await request.json()
    env = MaxwellDemonServiceManager().get().env(env_id=params['id'])
    return web.json_response(data=EnvResponseParams(env=base64_pickled(env)), status=200)
