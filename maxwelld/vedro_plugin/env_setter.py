import os
from _warnings import warn

from maxwelld.env_description.env_types import Environment


def setup_env_for_tests(env: Environment):
    updated_env = {}
    for service in env:
        for k, v in env[service].env.items():
            if k in updated_env and updated_env[k] != v:
                warn(
                    f'⚠️ env {k} tried to setup up multiple'
                    f' times with different values: {updated_env[k]} vs {v}'
                )
            updated_env[k] = v
            os.environ[k] = v
