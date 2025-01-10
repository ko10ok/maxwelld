import asyncio
import os
import pprint
import shlex
import sys
from asyncio import subprocess
from pathlib import Path

from rich.text import Text
from rtry import retry

from maxwelld.core.compose_data_types import ServicesComposeState
from maxwelld.core.config import Config
from maxwelld.core.utils.process_command_output import process_output_till_done
from maxwelld.helpers.jobs_result import JobResult
from maxwelld.helpers.jobs_result import OperationError
from maxwelld.output.console import CONSOLE
from maxwelld.output.styles import Style


class ComposeShellInterface:
    def __init__(self, compose_files, in_docker_project_root, execution_envs: dict = None):
        self.compose_files = compose_files
        self.in_docker_project_root = in_docker_project_root
        self.execution_envs = os.environ | {
            'COMPOSE_FILE': self.compose_files,
            'DOCKER_HOST': Config().docker_host,
            'COMPOSE_PROJECT_NAME': Config().compose_project_name,
        }
        if execution_envs is not None:
            self.execution_envs |= execution_envs
        self.verbose_docker_compose_commands = Config().verbose_docker_compose_commands
        self.debug_docker_compose_commands = Config().debug_docker_compose_commands
        self.verbose_docker_compose_ps_commands = Config().verbose_docker_compose_ps_commands
        self.extra_exec_params = Config().docker_compose_extra_exec_params

    @retry(attempts=10, delay=1, until=lambda x: x == JobResult.BAD)
    async def dc_state(self, env: dict = None, root: Path | str = None) -> ServicesComposeState | OperationError:
        sys.stdout.flush()

        if env is None:
            env = {}
        env = self.execution_envs | env

        if root is None:
            root = self.in_docker_project_root

        process = await asyncio.create_subprocess_shell(
            cmd := f"/usr/local/bin/docker-compose --project-directory {root}" + " ps -a --format='{{json .}}'",
            env=env,
            cwd=root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        CONSOLE.print(Text(
            f'{cmd}',
            style=Style.context
        ))
        stdout, stderr = await process_output_till_done(process, self.verbose_docker_compose_ps_commands)

        if process.returncode != 0:
            print(f"Can't get container's status {stdout} {stderr}")
            return OperationError(f'Stdout:\n{stdout}\n\nStderr:\n{stderr}')

        state_result = ServicesComposeState(stdout.decode('utf-8'))
        CONSOLE.print(Text('Services status result:', style=Style.info))
        CONSOLE.print(state_result.as_rich_text())
        return state_result

    @retry(attempts=3, delay=1, until=lambda x: x == JobResult.BAD)
    async def dc_up(self, services: list[str], env: dict = None, root: Path | str = None) -> JobResult | OperationError:
        sys.stdout.flush()

        if env is None:
            env = {}
        env = self.execution_envs | env

        if root is None:
            root = self.in_docker_project_root

        process = await asyncio.create_subprocess_shell(
            cmd := f'/usr/local/bin/docker-compose --project-directory {root} up --timestamps --no-deps --pull missing '
                   '--timeout 300 -d ' + ' '.join(services),
            env=env,
            cwd=root,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        debug = f'; in {root}; with {pprint.pformat(env)}' if self.debug_docker_compose_commands else ''
        CONSOLE.print(Text(
            f'{cmd}',
            style=Style.context
        ) + ' ' + Text(
            f'{debug}',
            style=Style.regular
        ))
        stdout, stderr = await process_output_till_done(process, self.verbose_docker_compose_commands)

        if process.returncode != 0:
            print("Can't up environment")
            state_result = await self.dc_state()
            if state_result == JobResult.GOOD:
                return OperationError(
                    f'Stdout:\n{stdout}\n\nStderr:\n{stderr}\n\nComposeState:\n{state_result.as_rich_text()}'
                )
            return OperationError(f'Stdout:\n{stdout}\n\nStderr:\n{stderr}\n\nComposeState:\n{state_result}')

        return JobResult.GOOD

    @retry(attempts=3, delay=1, until=lambda x: x == JobResult.BAD)
    async def dc_logs(self, services: list[str], env: dict = None, root: Path | str = None, logs_param='--no-log-prefix'
                      ) -> tuple[JobResult, bytes] | tuple[OperationError, None]:
        sys.stdout.flush()

        if env is None:
            env = {}
        env = self.execution_envs | env

        if root is None:
            root = self.in_docker_project_root

        if services is None:
            services = []
        services = ' '.join(services)

        process = await asyncio.create_subprocess_shell(
            cmd := f'/usr/local/bin/docker-compose --project-directory {root} logs {logs_param} {services}',
            env=env,
            cwd=root,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        CONSOLE.print(Text(
            f'{cmd}',
            style=Style.context
        ))
        stdout, stderr = await process_output_till_done(process, False)

        if process.returncode != 0:
            print(f"Can't get {services} logs")
            state_result = await self.dc_state()
            if state_result == JobResult.GOOD:
                return OperationError(
                    f'Stdout:\n{stdout}\n\nStderr:\n{stderr}\n\nComposeState:\n{state_result.as_rich_text()}'
                ), None
            return OperationError(f'Stdout:\n{stdout}\n\nStderr:\n{stderr}\n\nComposeState:\n{state_result}'), None

        return JobResult.GOOD, stdout

    @retry(attempts=3, delay=1, until=lambda x: x == JobResult.BAD)
    async def dc_exec(self, container: str, cmd: str, env: dict = None, root: Path | str = None
                      ) -> tuple[JobResult, bytes, bytes] | tuple[OperationError, bytes, bytes]:
        print(f'Executing {cmd} in {container} container')
        sys.stdout.flush()

        if env is None:
            env = {}
        env = self.execution_envs | env

        if root is None:
            root = self.in_docker_project_root

        process = await asyncio.create_subprocess_shell(
            cmd := f'/usr/local/bin/docker-compose --project-directory {root} exec {self.extra_exec_params} {container} {cmd}',
            env=env,
            cwd=root,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        debug = f'; in {root}; with {env}' if self.debug_docker_compose_commands else ''
        CONSOLE.print(Text(
            f'{cmd}',
            style=Style.context
        ) + ' ' + Text(
            f'{debug}',
            style=Style.regular
        ))
        stdout, stderr = await process_output_till_done(process, self.verbose_docker_compose_commands)

        if process.returncode != 0:
            print(f"Can't execute {cmd} in {container} successfully:\n{stdout=}, {stderr=}")
            state_result = await self.dc_state()
            if state_result == JobResult.GOOD:
                return OperationError(
                    f'Stdout:\n{stdout}\n\nStderr:\n{stderr}\n\nComposeState:\n{state_result.as_rich_text()}'
                ), stdout, stderr
            return OperationError(
                f'Stdout:\n{stdout}\n\nStderr:\n{stderr}\n\nComposeState:\n{state_result}'
            ), stdout, stderr

        return JobResult.GOOD, stdout, stderr

    async def dc_exec_process_pids(self, container: str,
                                   cmd: str,
                                   env: dict = None,
                                   root: Path | str = None,
                                   ) -> tuple[JobResult, bytes, bytes] | list[int] | tuple[OperationError, bytes, bytes]:
        if env is None:
            env = {}
        env = self.execution_envs | env

        if root is None:
            root = self.in_docker_project_root

        process_state = await asyncio.create_subprocess_shell(
            cmd := f'/usr/local/bin/docker-compose --project-directory {root} exec {self.extra_exec_params} {container} pgrep -fnx {shlex.quote(cmd)}',
            env=env,
            cwd=root,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process_state.communicate()
        pids_string = stdout.decode('utf-8')
        pids = []
        if pids_string != '':
            CONSOLE.print(f'Process still running: {cmd} in {container} on pids: {pids_string}')
            pids = [int(pid) for pid in pids_string.split(' ')]
        else:
            CONSOLE.print(f'Process done: {cmd} in {container}')
        return pids

    async def dc_exec_till_complete(self, container: str,
                                    cmd: str,
                                    env: dict = None,
                                    root: Path | str = None
                                    ) -> tuple[JobResult, bytes, bytes] | tuple[OperationError, bytes, bytes]:
        result = await self.dc_exec(container, cmd, env, root)
        await retry(attempts=30, delay=1, until=lambda x: x != [])(
            self.dc_exec_process_pids
        )(container, cmd)

        return result

    @retry(attempts=3, delay=1, until=lambda x: x == JobResult.BAD)
    async def dc_down(self, services: list[str], env: dict = None,
                      root: Path | str = None) -> JobResult | OperationError:
        print(f'Downing {services} containers')
        sys.stdout.flush()

        if env is None:
            env = {}
        env = self.execution_envs | env

        if root is None:
            root = self.in_docker_project_root

        process = await asyncio.create_subprocess_shell(
            cmd := f'/usr/local/bin/docker-compose --project-directory {root} down ' + ' '.join(services),
            env=env,
            cwd=root,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        debug = f'; in {root}; with {env}' if self.debug_docker_compose_commands else ''
        CONSOLE.print(Text(
            f'{cmd}',
            style=Style.context
        ) + ' ' + Text(
            f'{debug}',
            style=Style.regular
        ))
        stdout, stderr = await process_output_till_done(process, self.verbose_docker_compose_commands)

        if process.returncode != 0:
            # TODO swap print to CONSOLE
            print(f"Can't down {services} successfully")
            state_result = await self.dc_state()
            if state_result == JobResult.GOOD:
                return OperationError(
                    f'Stdout:\n{stdout}\n\nStderr:\n{stderr}\n\nComposeState:\n{state_result.as_rich_text()}'
                )
            return OperationError(f'Stdout:\n{stdout}\n\nStderr:\n{stderr}\n\nComposeState:\n{state_result}')

        return JobResult.GOOD
