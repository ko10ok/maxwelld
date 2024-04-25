from aiohttp import web
from aiohttp.web_request import Request

from maxwelld.version import get_version


async def healthcheck(request: Request) -> web.Response:
    return web.json_response({
        'status': 'ok',
        'version': get_version()
    })
