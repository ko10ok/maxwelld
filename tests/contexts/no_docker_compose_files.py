import os
from pathlib import Path

from config import Config


def no_docker_compose_files():
    for parent, dirs, files in os.walk(Config.COMPOSE_FILES_PATH):
        for filename in files:
            os.remove(Path(parent) / filename)
