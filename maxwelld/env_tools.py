from warnings import warn

from .env_types import Service
from .env_types import ServiceMode


def singleton(service: Service) -> Service:
    return Service(
        name=service.name,
        env=service.env,
        events_handlers=service.events_handlers,
        mode=ServiceMode.SINGLETON
    )


def off(service: Service) -> Service:
    warn('will be deprecated')
    return Service(
        name=service.name,
        env=service.env,
        events_handlers=service.events_handlers,
        mode=ServiceMode.OFF
    )
