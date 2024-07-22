from typing import TypedDict

from aiohttp import web
from aiohttp.web_request import Request

from maxwelld.client.types import EnvironmentId
from maxwelld.core.service import MaxwellDemonServiceManager
from maxwelld.helpers.bytes_pickle import base64_pickled


class DcLogsRequestParams(TypedDict):
    env_id: EnvironmentId
    services: list[str]


class DcLogsResponseParams(TypedDict):
    logs: str


async def dc_logs(request: Request) -> web.Response:
    params: DcLogsRequestParams = await request.json()

    logs = await MaxwellDemonServiceManager().get().logs(
        env_id=params['env_id'],
        services=params['services'],
    )

    return web.json_response(DcLogsResponseParams(logs=base64_pickled(logs)), status=200)
