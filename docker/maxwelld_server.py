import os
import pickle

from aiohttp import web
from aiohttp.web_request import Request

from maxwelld import MaxwellDemonService
from maxwelld.server.request_types import RequestType

routes = web.RouteTableDef()


async def index(request: Request) -> web.Response:
    params: RequestType = pickle.loads(await request.read())

    env = MaxwellDemonService(os.environ['COMPOSE_PROJECT_NAME'], request).up_compose(
        name=params['name'],
        config_template=params['config_template'],
        compose_files=params['compose_files'],
        isolation=params['isolation'],
        parallelism_limit=params['parallelism_limit'],
    )
    return web.json_response(data=pickle.dumps(env), status=200)


app = web.Application()
app.add_routes([
    web.get('/v0/up', index),
])
web.run_app(app, port=os.environ.get('PORT', 80))
