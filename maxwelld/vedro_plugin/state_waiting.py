from enum import Enum
from enum import auto
from functools import partial
from typing import Awaitable
from typing import Callable
from typing import List

from rich.text import Text
from rtry import retry

from maxwelld.core.docker_compose_interface import ComposeHealth
from maxwelld.core.docker_compose_interface import ComposeState
from maxwelld.core.docker_compose_interface import ServiceComposeState
from maxwelld.core.docker_compose_interface import ServicesComposeState
from maxwelld.helpers.countdown_counter import CountdownCounterKeeper
from maxwelld.helpers.state_keeper import ServicesState
from maxwelld.helpers.state_keeper import StateKeeper
from maxwelld.output.console import CONSOLE
from maxwelld.output.styles import Style


def is_service_running_and_healthy(service_state: ServiceComposeState) -> bool:
    return (service_state.state != ComposeState.RUNNING
            or service_state.health not in (ComposeHealth.EMPTY, ComposeHealth.HEALTHY))


class JobResult(Enum):
    GOOD = auto()
    BAD = auto()


async def check_all_services_up(
        get_services_state: Callable[[], Awaitable[ServicesComposeState]],
        services: List[str],
        counter_keeper: CountdownCounterKeeper,
        state_keeper: StateKeeper,
) -> JobResult:
    output_style = Style()

    if state_keeper.in_state(ServicesState.FIRST_STATE):
        CONSOLE.print(Text('Starting services check up', style=output_style.info))
        state_keeper.update_state(ServicesState.DEFAULT_STATE)

    services_state = await get_services_state()
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
        return JobResult.GOOD

    if state_keeper.not_in_state(services_state):
        CONSOLE.print(Text(' ✗ Still not ready:', style=output_style.bad))
        CONSOLE.print(services_state.as_rich_text(
            filter=is_service_running_and_healthy,
            style=output_style
        ))
        state_keeper.update_state(services_state)

    counter_keeper.tick()
    if counter_keeper.is_done():
        CONSOLE.print(Text(' ✗ Stop retries. Services still not ready:',
                           style=output_style.bad))
        CONSOLE.print(services_state.as_rich_text(
            style=output_style
        ))
    return JobResult.BAD


def wait_all_services_up(
        attempts=100,
        delay_s=3
) -> Callable[[Callable, list[str]], ServicesComposeState]:
    return retry(
        attempts=attempts,
        delay=delay_s,
        until=lambda x: x != JobResult.GOOD
    )(
        partial(
            check_all_services_up,
            counter_keeper=CountdownCounterKeeper(attempts),
            state_keeper=StateKeeper()
        )
    )
