import os

import vedro


class Config(vedro.Config):
    MAXWELLD_HOST = 'http://maxwelld'
    COMPOSE_FILES_PATH = '/compose-files'
    ROOT_PATH = os.environ.get('PWD')
