class CountdownCounterKeeper:
    def __init__(self, max_retries: int):
        self._count = 1
        self._max_retries = max_retries

    def tick(self):
        self._count += 1

    def is_done(self):
        return self._count > self._max_retries
