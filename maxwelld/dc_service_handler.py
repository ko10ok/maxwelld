from functools import partial
from typing import Callable
from typing import List

from rich.text import Text
from rtry import retry

from .docker_compose_interface import ComposeHealth
from .docker_compose_interface import ComposeState
from .docker_compose_interface import ServiceComposeState
from .docker_compose_interface import ServicesComposeState
from .output import CONSOLE
from .styles import Style


def is_service_running_and_healthy(service_state: ServiceComposeState) -> bool:
    return (service_state.state != ComposeState.RUNNING
            or service_state.health not in (ComposeHealth.EMPTY, ComposeHealth.HEALTHY))


def wait_all_services_up(attempts=100, delay_s=3) -> Callable[[], ServicesComposeState]:
    _previous_state = None
    attempt = 0

    def check_all_services_up(
            get_services_state: Callable[[], ServicesComposeState],
            services: List[str]
    ):
        output_style = Style()
        nonlocal _previous_state
        if _previous_state is None:
            CONSOLE.print(Text('Starting services check up', style=output_style.info))

        services_state = get_services_state()
        all_up = (all([
            service.state == ComposeState.RUNNING
            for service in services_state if service.name in services
        ]) and all([
            service.health in (ComposeHealth.EMPTY, ComposeHealth.HEALTHY)
            for service in services_state if service.name in services
        ]))

        if all_up:
            CONSOLE.print(Text(' ✔ All services up:', style=output_style.good))
            CONSOLE.print(services_state.as_rich_text(style=output_style))
            return 0

        if _previous_state != services_state:
            CONSOLE.print(Text(' ✗ Still not ready:', style=output_style.bad))
            CONSOLE.print(services_state.as_rich_text(
                filter=is_service_running_and_healthy,
                style=output_style
            ))
            _previous_state = services_state

        nonlocal attempt
        attempt += 1
        if attempt >= attempts:
            CONSOLE.print(Text(' ✗ Stop retries. Services still not ready:', style=output_style.bad))
            CONSOLE.print(services_state.as_rich_text(
                style=output_style
            ))
        return -1

    return retry(
        attempts=attempts,
        delay=delay_s,
        until=lambda x: x != 0
    )(
        partial(check_all_services_up)
    )
