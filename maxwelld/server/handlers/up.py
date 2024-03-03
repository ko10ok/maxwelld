import asyncio
import os
from typing import TypedDict

from aiohttp import web
from aiohttp.web_request import Request

from maxwelld.client.types import EnvironmentId
from maxwelld.core.service import MaxwellDemonService
from maxwelld.helpers.bytes_pickle import debase64_pickled

UP_LOCK = asyncio.Lock()


class UpRequestParams(TypedDict):
    name: str
    config_template: str
    compose_files: str
    isolation: bool
    parallelism_limit: int
    non_stop_containers: list[str]


class UpResponseParams(TypedDict):
    env_id: EnvironmentId
    new: bool


async def up_compose(request: Request) -> web.Response:
    params: UpRequestParams = await request.json()
    async with UP_LOCK:
        env_id, new = MaxwellDemonService(
            os.environ['COMPOSE_PROJECT_NAME'],
            params['non_stop_containers']
        ).up_compose(
            name=params['name'],
            config_template=debase64_pickled(params['config_template']),
            compose_files=params['compose_files'],
            isolation=params['isolation'],
            parallelism_limit=params['parallelism_limit'],
        )
    return web.json_response(UpResponseParams(env_id=env_id, new=new), status=200)
