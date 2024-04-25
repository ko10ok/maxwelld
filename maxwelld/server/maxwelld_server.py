import os

from aiohttp import web

from maxwelld.server.commands import HEALTHCHECK_PATH, UP_PATH, STATUS_PATH, ENV_PATH
from maxwelld.server.handlers.env import http_get_env
from maxwelld.server.handlers.healthcheck import healthcheck
from maxwelld.server.handlers.status import http_get_status
from maxwelld.server.handlers.up import up_compose

routes = web.RouteTableDef()

app = web.Application()
app.add_routes([
    web.get(HEALTHCHECK_PATH, healthcheck),
    web.post(UP_PATH, up_compose),
    web.get(STATUS_PATH, http_get_status),
    web.get(ENV_PATH, http_get_env),
])


def run_server():
    web.run_app(app, port=os.environ.get('PORT', 80))
