from typing import List

from vedro.core import ScenarioOrderer, VirtualScenario

from .scenario_tag_processing import extract_scenario_config


class EnvTagsOrderer(ScenarioOrderer):
    async def sort(self, scenarios: List[VirtualScenario]) -> List[VirtualScenario]:
        copied = scenarios[:]

        return sorted(
            copied,
            key=lambda x: extract_scenario_config(x)
        )
