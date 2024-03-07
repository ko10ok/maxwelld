import shlex
import subprocess
from pathlib import Path
from sys import stdout

from rich.text import Text
from rtry import retry

from maxwelld.core.compose_data_types import ServicesComposeState
from maxwelld.output.console import CONSOLE
from maxwelld.output.styles import Style
from maxwelld.vedro_plugin.state_waiting import JobResult


@retry(attempts=10, delay=1, until=lambda x: x == JobResult.BAD)
def dc_state(env: dict, root: Path | str) -> JobResult | ServicesComposeState:
    stdout.flush()
    status = subprocess.run(
        shlex.split("docker-compose --project-directory . ps -a --format='{{json .}}'"),
        env=env,
        cwd=root,
        capture_output=True,
    )
    if status.returncode != 0:
        print("Can't get container's status")
        return JobResult.BAD

    state_result = ServicesComposeState(status.stdout.decode('utf-8'))
    CONSOLE.print(Text('Services status result:', style=Style.info))
    CONSOLE.print(state_result.as_rich_text())
    return state_result


@retry(attempts=3, delay=1, until=lambda x: x == JobResult.BAD)
def dc_up(services: list[str], env: dict, root: Path | str) -> JobResult:
    stdout.flush()
    up = subprocess.run(
        ['docker-compose', '--project-directory', '.', 'up', '--timestamps', '--no-deps', '--pull', 'never',
         '--timeout', '300', '-d', *services],
        env=env,
        cwd=root,
    )
    if up.returncode != 0:
        print("Can't up entire environment")
        dc_state(env, root)
        return JobResult.BAD

    return JobResult.GOOD


@retry(attempts=3, delay=1, until=lambda x: x == JobResult.BAD)
def dc_exec(container: str, cmd: list[str], env: dict, root: Path | str) -> JobResult:
    print(f'Executing in {container} container: {cmd}')
    stdout.flush()
    hook = subprocess.run(
        [
            'docker-compose', '--project-directory', '.',
            'exec', f'{container}', *cmd
        ],
        env=env,
        cwd=root,
    )
    if hook.returncode != 0:
        print(f"Can't execute {cmd} in {container} successfully")
        dc_state(env, root)
        return JobResult.BAD

    return JobResult.GOOD
