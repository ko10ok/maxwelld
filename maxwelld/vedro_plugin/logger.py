from enum import Enum
from enum import auto

from rich.text import Text

from maxwelld.output.styles import Style


class WaitVerbosity(Enum):
    ON_ERROR = auto()
    COMPACT = auto()
    FULL = auto()


class Logger:
    def __init__(self, console):
        self._console = console
        self._log: Text | None = None

    def log(self, text: Text):
        if self._log is None:
            self._log = text
            return
        self._log.append(Text('\n', style=Style.regular).append(text))

    def flush(self):
        if self._log:
            self._console.print(self._log + Text(' ', style=Style.regular))
#
#
# Log = namedtuple('Log', ['text', 'level'])


# class Logger:
#     def __init__(self, console):
#         self._console = console
#         self._log: list[Log] = []
#
#     def log(self, text: Text, level: WaitVerbosity):
#         if self._log is None:
#             self._log = text
#             return
#         self._log += [
#             Log(text=Text('\n', style=Style.regular).append(text), level=level),
#         ]
#
#     def flush(self, level: WaitVerbosity):
#         if self._log:
#             self._console.print(reduce(operator.add, [
#                 log for log in self._log if log.level >= level
#             ]) + Text(' ', style=Style.regular))
#         self._log = []
