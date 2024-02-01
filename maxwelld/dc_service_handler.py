from typing import Callable
from typing import Dict
from typing import List

from rtry import retry


def service_status_str(service):
    return (f"{service['Service']:{20}}{service['State']:{20}}"
            f"{service['Health']:{20}}{service['Status']}")


def services_status_str(services_state):
    return '\n'.join([service_status_str(service_state) for service_state in services_state])


def not_ready_services_status_str(services_state):
    return '\n'.join([
        service_status_str(service_state) for service_state in services_state
        if service_state['State'] != 'running'
           or service_state['Health'] not in ('', 'healthy')
    ])


_previous_state = ''


def check_all_services_up(get_services_state: Callable[[], List[Dict]], services: List[str]):
    services_state = get_services_state()
    all_up = (all([
        s['State'] == 'running' for s in services_state if s['Service'] in services
    ]) and all([
        s['Health'] in ('', 'healthy') for s in services_state if s['Service'] in services
    ]))

    if all_up:
        print('All services up:')
        print(services_status_str(services_state))
        return 0

    current_state = not_ready_services_status_str(services_state)
    global _previous_state
    if _previous_state[:60] != current_state[:60]:
        print('Still not ready:')
        print(not_ready_services_status_str(services_state))
        _previous_state = current_state
    return -1


def wait_all_services_up(attempts=100, delay_s=3):
    print('Starting services check up')
    return retry(attempts=attempts, delay=delay_s, until=lambda x: x != 0)(check_all_services_up)
