import sys
from enum import Enum
from enum import auto
from functools import partial
from functools import reduce
from sys import exit
from typing import Type
from typing import Union

import vedro.events
from rich.text import Text
from vedro.core import ConfigType
from vedro.core import Dispatcher
from vedro.core import Plugin
from vedro.core import PluginConfig
from vedro.events import ArgParseEvent
from vedro.events import ArgParsedEvent
from vedro.events import ConfigLoadedEvent
from vedro.events import ScenarioRunEvent
from vedro.events import StartupEvent

from maxwelld.client.maxwell_client import MaxwellDemonClient
from maxwelld.core.sequence_run_types import ComposeConfig
from maxwelld.env_description.env_types import Environments
from maxwelld.helpers.jobs_result import JobResult
from maxwelld.output.console import CONSOLE
from maxwelld.output.styles import Style
from maxwelld.vedro_plugin.env_setter import setup_env_for_tests
from maxwelld.vedro_plugin.logger import WaitVerbosity
from maxwelld.vedro_plugin.scenario_ordering import EnvTagsOrderer
from maxwelld.vedro_plugin.scenario_tag_processing import extract_scenario_config
from maxwelld.vedro_plugin.scenario_tag_processing import extract_scenarios_configs_set
from maxwelld.vedro_plugin.state_waiting import wait_all_services_up

DEFAULT_COMPOSE = 'default'


class Stage(Enum):
    INIT = auto()
    PRE_TEST = auto()


class VedroMaxwellPlugin(Plugin):
    def __init__(self, config: Type["VedroMaxwell"]) -> None:
        super().__init__(config)
        self._enabled = config.enabled
        self._envs: Environments = config.envs
        self._maxwell_demon = MaxwellDemonClient(host="http://127.0.0.1")
        if config.maxwell_demon_client:
            self._maxwell_demon = config.maxwell_demon_client
        self._list_envs = None

        self._compose_configs: dict[str, ComposeConfig] = config.compose_cfgs
        assert DEFAULT_COMPOSE in self._compose_configs, \
            'Need to set up at least {DEFAULT_COMPOSE: ComposeConfig(...)} config'
        self._compose_choice_name: str = DEFAULT_COMPOSE
        self._compose_choice: Union[ComposeConfig, None] \
            = self._compose_configs[self._compose_choice_name]
        self._force_env_name: Union[str, None] = None
        self._chosen_config_name_postfix: str = ''
        self._checked_envs = []
        self._wait_all_service_func = config.wait_all_service_func
        self._force_restart = False

        self._lats_env_name_started = None
        self._lats_env_id_started = None

        self._reported_full = False
    def _print_running_config(self):
        CONSOLE.print(
            Text('Running ', style=Style.info)
            .append(Text(self._compose_choice_name, style=Style.mark))
            .append(Text(' compose config: '))
            .append(Text(str(self._compose_choice), style=Style.mark))
        )
        if self._force_env_name:
            CONSOLE.print(f'Overriding configuration for tests: {self._force_env_name}')

    def subscribe(self, dispatcher: Dispatcher) -> None:
        if not self._enabled:
            return

        dispatcher.listen(ConfigLoadedEvent, self.on_config_loaded) \
            .listen(vedro.events.ArgParseEvent, self.handle_arg_parse) \
            .listen(vedro.events.ArgParsedEvent, self.handle_arg_parsed) \
            .listen(vedro.events.StartupEvent, self.handle_scenarios) \
            .listen(vedro.events.ScenarioRunEvent, self.handle_setup_test_config)

    def on_config_loaded(self, event: ConfigLoadedEvent) -> None:
        self._global_config: ConfigType = event.config

    async def wait_env_ready(self, env_id, verbose: WaitVerbosity) -> None:
        environment = await self._maxwell_demon.env(env_id)

        checker = self._wait_all_service_func.make_checker()

        up_result = await checker(
            get_services_state=partial(self._maxwell_demon.status, env_id=env_id),
            services=environment.get_services(),
            verbose=verbose,
        )
        assert up_result != JobResult.BAD, f"Can't done up environment"

    async def up_env(self, env_name, stage):
        if (self._verbose and not self._reported_full) or stage == Stage.INIT:
            CONSOLE.print(
                Text('Starting ', style=Style.regular)
                .append(Text(env_name, style=Style.mark))
                .append(Text(' services for tests ...', style=Style.regular))
            )

        env = getattr(self._envs, env_name)
        started_env_id = await self._maxwell_demon.up(
            name=env_name + self._chosen_config_name_postfix,
            config_template=env,
            compose_files=self._compose_choice.compose_files,
            parallelism_limit=self._compose_choice.parallel_env_limit,
            force_restart=self._force_restart
        )

        verbose = WaitVerbosity.COMPACT
        if self._lats_env_id_started == started_env_id:
            verbose = WaitVerbosity.ON_ERROR
        if self._verbose and not self._reported_full:
            verbose = WaitVerbosity.FULL

        await self.wait_env_ready(
            env_id=started_env_id,
            verbose=verbose
        )

        self._force_restart = False
        self._reported_full = True
        self._lats_env_id_started = started_env_id
        return started_env_id

    async def handle_scenarios(self, event: StartupEvent) -> None:
        needed_configs = extract_scenarios_configs_set(event.scheduler.scheduled)

        CONSOLE.print(
            Text(f'Tests requests configs: ') + reduce(
                lambda a, b: a + Text(', ', style=Style.regular) + b, [
                    Text(f'{cfg}', style=Style.mark) for cfg in needed_configs
                ]
            )
        )

        if self._force_env_name:
            config_env_name = self._force_env_name
            CONSOLE.print(f'Overriding tests config:{needed_configs} '
                          f'by --env={self._force_env_name}')
            needed_configs = {config_env_name}

        if self._list_envs:
            sys.exit()

        if (
                self._compose_choice.parallel_env_limit
                and (len(needed_configs) > self._compose_choice.parallel_env_limit)
        ):
            self._global_config.Registry.ScenarioOrderer.register(EnvTagsOrderer, self)

        if (
                (self._compose_choice.parallel_env_limit is None)
                or (self._compose_choice.parallel_env_limit == len(needed_configs))
        ):
            for cfg_name in list(needed_configs):
                await self._maxwell_demon.healthcheck()
                await self.up_env(cfg_name, Stage.INIT)

    async def handle_setup_test_config(self, event: ScenarioRunEvent):
        config_env_name = extract_scenario_config(event.scenario_result.scenario)

        if self._force_env_name:
            if self._verbose:
                CONSOLE.print(f'Overriding tests config: '
                              f'{config_env_name} by --md-env={self._force_env_name}')
            config_env_name = self._force_env_name

        env_id = await self.up_env(config_env_name, Stage.PRE_TEST)

        environment = await self._maxwell_demon.env(env_id)
        setup_env_for_tests(environment)

    def handle_arg_parse(self, event: ArgParseEvent) -> None:
        group = event.arg_parser.add_argument_group("Maxwell Demon")
        group.add_argument("--md-list-envs",
                           action='store_true',
                           help="List possible enviroments")

        for choice_name, config in self._compose_configs.items():
            default_text = '[set by default]' if choice_name == DEFAULT_COMPOSE else ''
            group.add_argument(f"--md-{choice_name}",
                               action='store_true',
                               help=f"Choose compose config {default_text}: {config}")

        group.add_argument("--md-fr",
                           action='store_true',
                           help="Force restart env")

        group.add_argument("--md-list-services",
                           action='store_true',
                           help="List possible enviroments")

        group.add_argument("--md-env",
                           type=str,
                           choices=list(self._envs.list_all()),
                           help="Up choosen enviroment")

        group.add_argument("--md-v",
                           action='store_true',
                           help="List possible enviroments")

        group.add_argument("--md-parallel-env-limit",
                           type=int,
                           help="Max of parallel running envs, unused will be killed when extra "
                                "one needs")

    def handle_arg_parsed(self, event: ArgParsedEvent) -> None:
        self._parallel_env_limit = event.args.md_parallel_env_limit
        self._verbose = event.args.md_v

        for choice_name, config in self._compose_configs.items():
            if getattr(event.args, f'md_{choice_name}'):
                self._compose_choice_name = choice_name
                self._compose_choice = config
                self._parallel_env_limit = config.parallel_env_limit
                if choice_name != DEFAULT_COMPOSE:
                    self._chosen_config_name_postfix = f'_{choice_name}'

        self._list_envs = event.args.md_list_envs
        if self._list_envs:
            self._maxwell_demon.list_current_in_flight_envs(self._envs.list_all())
            exit(0)

        if event.args.md_list_services:
            self._maxwell_demon.list_services()
            exit(0)

        if event.args.md_env:
            self._force_env_name = event.args.md_env

        if event.args.md_fr:
            self._force_restart = event.args.md_fr

        self._print_running_config()


class VedroMaxwell(PluginConfig):
    plugin = VedroMaxwellPlugin

    # Enables plugin
    enabled = False

    # Maxwell environments
    envs: Environments = None

    # Maxwell Demon To control the world
    maxwell_demon_client: MaxwellDemonClient = None

    # ComposeConfig set of compose files and defaulr parallelism restrictions
    compose_cfgs: dict[str, ComposeConfig] = None

    # services waiter
    wait_all_service_func = wait_all_services_up()
