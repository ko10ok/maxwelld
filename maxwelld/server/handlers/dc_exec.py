from typing import TypedDict

from aiohttp import web
from aiohttp.web_request import Request

from maxwelld.client.types import EnvironmentId
from maxwelld.core.service import MaxwellDemonServiceManager
from maxwelld.helpers.bytes_pickle import base64_pickled


class DcExecRequestParams(TypedDict):
    env_id: EnvironmentId
    container: str
    command: str
    till_complete: bool


class DcExecResponseParams(TypedDict):
    output: str


async def dc_exec(request: Request) -> web.Response:
    params: DcExecRequestParams = await request.json()

    output = await MaxwellDemonServiceManager().get().exec(
        env_id=params['env_id'],
        container=params['container'],
        command=params['command'],
        till_complete=params.get('till_complete', False),
    )
    
    return web.json_response(DcExecResponseParams(output=base64_pickled(output)), status=200)
