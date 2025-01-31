from typing import TypedDict

from aiohttp import web
from aiohttp.web_request import Request

from maxwelld.client.types import EnvironmentId
from maxwelld.core.service import MaxwellDemonServiceManager
from maxwelld.helpers.bytes_pickle import base64_pickled


class DcExecLogsRequestParams(TypedDict):
    uid: str


class DcExecLogsResponseParams(TypedDict):
    output: str


async def dc_exec_logs(request: Request) -> web.Response:
    params: DcExecLogsRequestParams = await request.json()

    output = await MaxwellDemonServiceManager().get().get_exec_logs(
        uid=params['uid'],
    )
    
    return web.json_response(DcExecLogsResponseParams(output=base64_pickled(output)), status=200)
