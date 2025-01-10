import httpx


class MaxwelldApi:
    def __init__(self):
        self.base_url = 'http://maxwelld'
        self.client = httpx.AsyncClient()

    async def up(self, params, headers=None):
        return await self.client.post(
            f'{self.base_url}/dc/up',
            json=params,
            headers=headers,
            timeout=360,
        )

    async def exec(self, params):
        return await self.client.post(
            f'{self.base_url}/dc/exec',
            json=params,
            timeout=360,
        )

    async def logs(self, params):
        return await self.client.post(
            f'{self.base_url}/dc/logs',
            json=params,
            timeout=360,
        )
