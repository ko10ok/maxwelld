import httpx
from requests import Response


class FormattedResponse:
    def __init__(self, response: Response):
        self.response = response

    @property
    def status_code(self):
        return self.response.status_code

    def text(self):
        return self.response.text

    def json(self):
        return self.response.json()

    def any_body(self):
        try:
            return self.response.json()
        except Exception:
            return self.response.text

    def __repr__(self):
        return (f'Response(\n'
                f'  status_code={self.status_code}\n'
                f'  json={self.any_body()}\n'
                f')')


class MaxwelldApi:
    def __init__(self):
        self.base_url = 'http://maxwelld'
        self.client = httpx.AsyncClient()

    async def up(self, params, headers=None):
        return FormattedResponse(await self.client.post(
            f'{self.base_url}/dc/up',
            json=params,
            headers=headers,
            timeout=360,
        ))

    async def exec(self, params):
        return FormattedResponse(await self.client.post(
            f'{self.base_url}/dc/exec',
            json=params,
            timeout=360,
        ))

    async def logs(self, params):
        return FormattedResponse(await self.client.post(
            f'{self.base_url}/dc/logs',
            json=params,
            timeout=360,
        ))

    async def get_exec_logs(self, params):
        return FormattedResponse(await self.client.post(
            f'{self.base_url}/dc/get_exec_logs',
            json=params,
            timeout=360,
        ))
