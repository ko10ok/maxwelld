import json
import shlex
import subprocess

from typing import List


def dc_state(env, root) -> List:
    status = subprocess.run(
        shlex.split("docker-compose --project-directory . ps -a --format='{{json .}}'"),
        env=env,
        cwd=root,
        capture_output=True,
    )
    services_state = [
        json.loads(state_str)
        for state_str in status.stdout.decode('utf-8').split('\n')
        if state_str
    ]
    return services_state
