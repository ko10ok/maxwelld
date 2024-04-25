from copy import deepcopy
from enum import Enum
from enum import auto
from typing import TypeVar

T = TypeVar('T')


class ServicesState(Enum):
    FIRST_STATE = auto()
    DEFAULT_STATE = auto()


class StateKeeper:
    def __init__(self, state: T | ServicesState = ServicesState.FIRST_STATE):
        self._state: T | ServicesState = deepcopy(state)

    def in_state(self, new_state: T | ServicesState):
        return self._state == new_state

    def not_in_state(self, new_state: T | ServicesState):
        return self._state != new_state

    def update_state(self, new_state: T | ServicesState):
        self._state = deepcopy(new_state)
