import asyncio
from typing import TypedDict

from aiohttp import web
from aiohttp.web_request import Request

from maxwelld.client.types import EnvironmentId
from maxwelld.core.service import MaxwellDemonServiceManager
from maxwelld.helpers.bytes_pickle import base64_pickled

UP_LOCK = asyncio.Lock()


class StatusRequestParams(TypedDict):
    id: EnvironmentId


class StatusResponseParams(TypedDict):
    status: str


async def http_get_status(request: Request) -> web.Response:
    params: StatusRequestParams = await request.json()
    status = await MaxwellDemonServiceManager().get().status(env_id=params['id'])
    return web.json_response(StatusResponseParams(status=base64_pickled(status)), status=200)
