import asyncio
import sys
from asyncio import subprocess
from pathlib import Path

from rich.text import Text
from rtry import retry

from maxwelld.core.compose_data_types import ServicesComposeState
from maxwelld.output.console import CONSOLE
from maxwelld.output.styles import Style
from maxwelld.vedro_plugin.state_waiting import JobResult


@retry(attempts=10, delay=1, until=lambda x: x == JobResult.BAD)
async def dc_state(env: dict, root: Path | str) -> JobResult | ServicesComposeState:
    sys.stdout.flush()

    process = await asyncio.create_subprocess_shell(
        "docker-compose --project-directory . ps -a --format='{{json .}}'",
        env=env,
        cwd=root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    await process.wait()
    stdout, stderr = await process.communicate()
    if process.returncode != 0:
        print(f"Can't get container's status {stdout} {stderr}")
        return JobResult.BAD

    state_result = ServicesComposeState(stdout.decode('utf-8'))
    CONSOLE.print(Text('Services status result:', style=Style.info))
    CONSOLE.print(state_result.as_rich_text())
    return state_result


@retry(attempts=3, delay=1, until=lambda x: x == JobResult.BAD)
async def dc_up(services: list[str], env: dict, root: Path | str) -> JobResult:
    sys.stdout.flush()

    process = await asyncio.create_subprocess_shell(
        'docker-compose --project-directory . up --timestamps --no-deps --pull never '
        '--timeout 300 -d ' + ' '.join(services),
        env=env,
        cwd=root,
    )
    await process.wait()

    if process.returncode != 0:
        print("Can't up environment")
        await dc_state(env, root)
        return JobResult.BAD

    return JobResult.GOOD


@retry(attempts=3, delay=1, until=lambda x: x == JobResult.BAD)
async def dc_exec(container: str, cmd: str, env: dict, root: Path | str) -> JobResult:
    print(f'Executing {cmd} in {container} container')
    sys.stdout.flush()

    process = await asyncio.create_subprocess_shell(
        f'docker-compose --project-directory . exec {container} {cmd}',
        env=env,
        cwd=root,
    )
    await process.wait()

    if process.returncode != 0:
        print(f"Can't execute {cmd} in {container} successfully")
        await dc_state(env, root)
        return JobResult.BAD

    return JobResult.GOOD
