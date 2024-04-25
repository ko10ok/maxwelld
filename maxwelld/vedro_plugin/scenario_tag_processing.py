from typing import Iterator
from typing import List

from vedro.core import VirtualScenario

from maxwelld.env_description.env_types import DEFAULT_ENV
from maxwelld.env_description.env_types import Environment


def extract_scenario_config(scenario: VirtualScenario):
    scenario_env = DEFAULT_ENV
    if hasattr(scenario._orig_scenario, 'tags'):
        for tag in scenario._orig_scenario.tags:
            if isinstance(tag, Environment):
                scenario_env = str(tag)
    return scenario_env


def extract_scenarios_configs_set(scenarios: List[VirtualScenario] | Iterator[
    VirtualScenario]):
    needed_configs = set()
    for scenario in scenarios:
        needed_configs.add(extract_scenario_config(scenario))
    return needed_configs
