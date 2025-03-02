import json
from dataclasses import dataclass
from typing import Callable
from typing import Iterator

from rich.text import Text

from maxwelld.output.styles import Style


class ComposeState:
    RUNNING = 'running'
    EXITED = 'exited'


class ComposeHealth:
    EMPTY = ''
    HEALTHY = 'healthy'


@dataclass
class ServiceComposeState:
    name: str
    state: str
    exit_code: int
    health: str
    status: str  # "Up X seconds"
    labels: dict[str, str]

    @classmethod
    def from_json(cls, json_status: str) -> 'ServiceComposeState':
        status = json.loads(json_status)
        return cls(
            name=status['Service'],
            state=status['State'],
            exit_code=status['ExitCode'],
            health=status['Health'],
            status=status['Status'],
            labels={
                (label_split := label.split('=', maxsplit=2))[0]: label_split[1] if len(label_split) == 2 else None
                for label in status['Labels'].split(',')
                if 'Labels' in status
            },
        )

    def __eq__(self, other):
        return (isinstance(other, ServiceComposeState)
                and self.name == other.name
                and self.state == other.state
                and self.health == other.health
                and self.exit_code == self.exit_code)

    def __repr__(self):
        return (f'{type(self).__name__}'
                f'(name="{self.name}", '
                f'state="{self.state}", '
                f'exit_code="{self.exit_code}", '
                f'health="{self.health}", '
                f'status="{self.status}"\n'
                f'labels={self.labels}')

    def as_rich_text(self, style: Style = Style()):
        service_string = Text('     ')
        service_string.append(Text(f"{self.name:{30}}", style=style.regular))

        match (self.state, self.exit_code):
            case (ComposeState.RUNNING, _):
                style_result = style.good
            case (ComposeState.EXITED, 0):
                style_result = style.suspicious
            case _:
                style_result = style.bad
        service_string.append(Text(
            f"{self.state:{20}}",
            style=style_result
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
            'exit_code': self.exit_code,
            'health': self.health,
            'status': self.status,
            'labels': self.labels,
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
