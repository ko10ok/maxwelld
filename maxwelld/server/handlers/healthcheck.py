import os

from aiohttp import web
from aiohttp.web_request import Request

from maxwelld import version
from maxwelld.core.service import MaxwellDemonService


async def healthcheck(request: Request) -> web.Response:
    try:
        MaxwellDemonService(
            os.environ['COMPOSE_PROJECT_NAME'],
            non_stop_containers=[]
        )
    except Exception as e:
        web.Response(status=500, text=str(e))

    return web.json_response({
        'status': 'ok',
        'version': version.version
    })
