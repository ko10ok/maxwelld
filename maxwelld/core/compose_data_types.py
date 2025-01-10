import json
from dataclasses import dataclass
from typing import Callable
from typing import Iterator

from rich.text import Text

from maxwelld.output.styles import Style


class ComposeState:
    RUNNING = 'running'


class ComposeHealth:
    EMPTY = ''
    HEALTHY = 'healthy'


@dataclass
class ServiceComposeState:
    name: str
    state: str
    health: str
    status: str  # "Up X seconds"

    @classmethod
    def from_json(cls, json_status: str) -> 'ServiceComposeState':
        status = json.loads(json_status)
        return cls(
            name=status['Service'],
            state=status['State'],
            health=status['Health'],
            status=status['Status'],
        )

    def __eq__(self, other):
        return (isinstance(other, ServiceComposeState)
                and self.name == other.name
                and self.state == other.state
                and self.health == other.health)

    def __repr__(self):
        return (f'{type(self).__name__}'
                f'(name="{self.name}", '
                f'state="{self.state}", '
                f'health="{self.health}", '
                f'status="{self.status}")')

    def as_rich_text(self, style: Style = Style()):
        service_string = Text('     ')
        service_string.append(Text(f"{self.name:{20}}", style=style.regular))
        service_string.append(Text(
            f"{self.state:{20}}",
            style=style.good if self.state == ComposeState.RUNNING else style.bad
        ))
        service_string.append(Text(
            f"{self.health:{20}}",
            style=style.good if self.health == ComposeHealth.HEALTHY else style.bad
        ))
        service_string.append(Text(
            self.status, style=style.regular
        ))
        service_string.append(Text('\n', style=style.regular))
        return service_string

    def as_json(self) -> dict[str, str]:
        return {
            'name': self.name,
            'state': self.state,
            'health': self.health,
            'status': self.status,
        }


class ServicesComposeState:
    def __init__(self, compose_status: str):
        self._services: list[ServiceComposeState] = [
            ServiceComposeState.from_json(state_str)
            for state_str in compose_status.split('\n')
            if state_str
        ]

    def __contains__(self, item):
        return item in self._services

    def __iter__(self) -> Iterator[ServiceComposeState]:
        return iter(self._services)

    def as_rich_text(
        self,
        filter: Callable[[ServiceComposeState], bool] = lambda x: True,
        style: Style = Style()
    ) -> Text:
        services_text = Text()
        for service_state in self._services:
            if filter(service_state):
                services_text.append(service_state.as_rich_text(style))
        return services_text

    def __eq__(self, other) -> bool:
        if isinstance(other, ServicesComposeState):
            for service_state in self._services:
                if service_state not in other:
                    return False
            for service_state in other:
                if service_state not in self:
                    return False
            return True

        return False

    def __repr__(self):
        return f'{type(self).__name__}(<{self._services}>)'

    def as_json(self, filter: Callable[[ServiceComposeState], bool] = lambda x: True, ) -> list[dict]:
        return [service_status.as_json() for service_status in self._services if filter(service_status)]
