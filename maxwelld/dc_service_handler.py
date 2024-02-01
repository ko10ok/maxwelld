from typing import Callable
from typing import Dict
from typing import List

from rich.console import Console
from rich.text import Text
from rtry import retry

from .styles import Style


def service_status_str(service) -> Text:
    service_string = Text('     ')
    service_string.append(Text(f"{service['Service']:{20}}"))
    service_string.append(Text(
        f"{service['State']:{20}}",
        style=Style.good if service['State'] == 'running' else Style.bad
    ))
    service_string.append(Text(
        f"{service['Health']:{20}}",
        style=Style.good if service['Health'] == 'healthy' else Style.bad
    ))
    service_string.append(Text(
        service['Status']
    ))
    service_string.append(Text('\n'))
    return service_string


def services_status_str(services_state) -> Text:
    services_text = Text()
    for service_state in services_state:
        services_text.append(service_status_str(service_state))
    return services_text


def not_ready_services_status_str(services_state) -> Text:
    services_text = Text()
    for service_state in services_state:
        if service_state['State'] != 'running' or service_state['Health'] not in ('', 'healthy'):
            services_text.append(service_status_str(service_state))

    return services_text


_previous_state: Text | None = None


def check_all_services_up(get_services_state: Callable[[], List[Dict]], services: List[str]):
    con = Console()
    global _previous_state
    if _previous_state == None:
        con.print(Text('Starting services check up', style=Style.info))
        _previous_state = Text()

    services_state = get_services_state()
    all_up = (all([
        s['State'] == 'running' for s in services_state if s['Service'] in services
    ]) and all([
        s['Health'] in ('', 'healthy') for s in services_state if s['Service'] in services
    ]))


    if all_up:
        con.print(Text(' ✔ All services up:', style=Style.good))
        con.print(services_status_str(services_state))
        return 0

    current_state = not_ready_services_status_str(services_state)
    if _previous_state[:60] != current_state[:60]:
        con.print(Text(' ✗ Still not ready:', style=Style.bad))
        con.print(not_ready_services_status_str(services_state))
        _previous_state = current_state
    return -1


def wait_all_services_up(attempts=100, delay_s=3):
    _previous_state = Text()
    con = Console()

    return retry(attempts=attempts, delay=delay_s, until=lambda x: x != 0)(check_all_services_up)
