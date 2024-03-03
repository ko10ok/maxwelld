import os

from aiohttp import web

from maxwelld.server.commands import HEALTHCHECK
from maxwelld.server.commands import UP_PATH
from maxwelld.server.handlers.healthcheck import healthcheck
from maxwelld.server.handlers.up import up_compose

routes = web.RouteTableDef()

app = web.Application()
app.add_routes([
    web.get(HEALTHCHECK, healthcheck),
    web.post(UP_PATH, up_compose),
])


def run_server():
    web.run_app(app, port=os.environ.get('PORT', 80))
