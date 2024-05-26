from pathlib import Path

from maxwelld.core.sequence_run_types import ComposeInstanceFiles
from maxwelld.core.utils.compose_instance_cfg import get_new_instance_compose_files


def make_debug_bash_env(env_config_compose_instance: ComposeInstanceFiles,
                        host_tmp_env_path: Path):
    new_external_compose_file = get_new_instance_compose_files(
        env_config_compose_instance.compose_files_source,
        host_tmp_env_path / env_config_compose_instance.env_config_instance.env_id
    )

    with open(env_config_compose_instance.directory / '.env', 'w') as f:
        f.write(f'alias dc="docker-compose --project-directory ."\n')
        f.write(f'export COMPOSE_FILE={new_external_compose_file}\n')
        f.write(f'alias deactivate-env="unset COMPOSE_FILE"\n')
        # TODO Envs
        # for k,value in updated_envs.items():
        #     f.write(f'{k}={value}\n')
        # f.write(f'export COMPOSE_PROJECT_NAME={new_project_name}\n')
