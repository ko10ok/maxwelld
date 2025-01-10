import os

from aiohttp import web

from maxwelld.server.commands import DC_EXEC_PATH
from maxwelld.server.commands import DC_LOGS_PATH
from maxwelld.server.commands import DC_UP_PATH
from maxwelld.server.commands import ENV_PATH
from maxwelld.server.commands import HEALTHCHECK_PATH
from maxwelld.server.commands import STATUS_PATH
from maxwelld.server.commands import UP_PATH
from maxwelld.server.handlers.dc_exec import dc_exec
from maxwelld.server.handlers.dc_logs import dc_logs
from maxwelld.server.handlers.dc_up import dc_up
from maxwelld.server.handlers.env import http_get_env
from maxwelld.server.handlers.healthcheck import healthcheck
from maxwelld.server.handlers.status import http_get_status
from maxwelld.server.handlers.up import up_compose

routes = web.RouteTableDef()

app = web.Application()
app.add_routes([
    web.post(DC_UP_PATH, dc_up),
    web.post(DC_EXEC_PATH, dc_exec),
    web.post(DC_LOGS_PATH, dc_logs),

    # ============================
    web.get(HEALTHCHECK_PATH, healthcheck),
    web.post(UP_PATH, up_compose),
    web.get(STATUS_PATH, http_get_status),
    web.get(ENV_PATH, http_get_env),
])


def run_server():
    web.run_app(app, port=os.environ.get('PORT', 80))
