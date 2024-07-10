import httpx


class MaxwelldApi:
    def __init__(self):
        self.base_url = 'http://maxwelld'
        self.client = httpx.AsyncClient()

    async def up(self, params):
        return await self.client.post(
            f'{self.base_url}/dc/up',
            json=params,
            timeout=360,
        )
