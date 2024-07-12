from enum import Enum
from enum import auto
from typing import Dict
from typing import Iterator
from typing import List
from typing import NamedTuple

DEFAULT_ENV = 'DEFAULT'


class Environments:
    def __getitem__(self, item) -> 'Environment':
        return getattr(self, item)

    @classmethod
    def list_all(cls) -> list[str]:
        return [
            item
            for item in cls.__dict__
            if not item.startswith('__') or not item.startswith('_')
        ]


class AsIs:
    def __init__(self, value):
        self.value = value


class Env(Dict):
    ...


class StageName(NamedTuple):
    compose_name: str


class EventStage(Enum):
    BEFORE_ALL = StageName('before_all')
    BEFORE_SERVICE_START = StageName('before_start')
    AFTER_SERVICE_START = StageName('after_start')
    AFTER_SERVICE_HEALTHY = StageName('after_healthy')
    AFTER_ALL = StageName('after_all')

    @classmethod
    def get_all_stages(cls):
        return [
            cls.BEFORE_ALL,
            cls.BEFORE_SERVICE_START,
            cls.AFTER_SERVICE_START,
            cls.AFTER_SERVICE_HEALTHY,
            cls.AFTER_ALL,

        ]

    @classmethod
    def get_all_compose_stages(cls):
        return [stage.value.compose_name for stage in cls.get_all_stages()]

    @classmethod
    def get_compose_stage(cls, stage_name: str) -> 'EventStage':
        for stage in cls.get_all_stages():
            if stage.value.compose_name == stage_name:
                return stage
        assert False, 'No such stage: {}'.format(stage_name)


class Handler(NamedTuple):
    stage: EventStage
    cmd: str
    executor: str = None


class ServiceMode(Enum):
    ON = auto()
    OFF = auto()
    SINGLETON = auto()
    EXTERNAL = auto()


class Service(NamedTuple):
    name: str
    env: Env = Env()
    events_handlers: List[Handler] = []
    mode: ServiceMode = ServiceMode.ON

    def __eq__(self, other):
        return self.name == other.name

    def __repr__(self):
        return f'Service({self.name}, {self.mode})'

    def with_env(self, env: Env):
        return Service(
            name=self.name,
            env=Env(self.env | env),
            events_handlers=self.events_handlers,
            mode=self.mode
        )

    def as_dict(self):
        return {
            'name': self.name,
            'env': dict(self.env),
        }


def remove_dups(*services: Service) -> List[Service]:
    result_services = []
    for service in reversed(services):
        if service not in result_services:
            result_services += [service]

    return list(reversed(result_services))


class Environment:  # TODO rename Environment
    @classmethod
    def from_environment(cls, env: 'Environment', name, *services: Service):
        # TODO duplicated services merging
        return Environment(name, *env._services, *services)

    def __init__(self, name, *services: Service):
        # TODO duplicated services merging
        self._name = name  # TODO think how to extract from envs?
        self._services = remove_dups(*services)
        self._services_dict: dict[str, Service] = {
            item.name: item for item in self._services
        }

    def __str__(self) -> str:
        return self._name

    def __repr__(self):
        return f'Environment({self._name})'

    def get_services(self) -> dict:
        return self._services_dict

    def __getitem__(self, item) -> Service:
        return self._services_dict[item]

    def __iter__(self) -> Iterator[str]:
        return iter(self._services_dict)

    def isidentifier(self):
        return True

    def __eq__(self, other):
        return self._name == other

    def __hash__(self):
        return hash(self._name)

    def as_json(self) -> list[dict]:
        return [
            service.as_dict() for service in self._services
        ]


class SingletonService(Service):
    singleton: bool = False
