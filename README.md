# Maxwell's demon of test enviroment

Orchestrate testing env easily.

Wraps docker-compose and it's dependencies into it's own container with http api.

Execute docker-compose commands sequences for starting requested services set from volumed docker-compose files.
Rerun environment when in-flight one is different from new requested.

# Vedro usage
## Add "supervisor" container
```docker-compose
  maxwelld:
    image: docker.io/ko10ok/maxwelld:0.2.9
    volumes:
      - .:/project
      - ./docker-composes:/docker-composes
      - ./env-tmp:/env-tmp
    environment:
      - DOCKER_HOST=tcp://dockersock:2375
      - COMPOSE_PROJECT_NAME=${COMPOSE_PROJECT_NAME}
      - NON_STOP_CONTAINERS=dockersock,maxwelld,e2e
      - HOST_PROJECT_ROOT_DIRECTORY=${HOST_PROJECT_ROOT_DIRECTORY}
```

## Define services config
```python
# env_set.py
from maxwelld import Environments
from maxwelld import Environment
from maxwelld import DEFAULT_ENV
from maxwelld import Service

web = Service('web')
web_gallery = Service('web-gallery')  # Service names "web-gallery", "mq", etc from docker-compose.yml
mq = Service('mq')
db = Service('db')

class Envs(Environments):
    DEFAULT = Environment(
        DEFAULT_ENV,
        web, web_gallery,
        db,
        mq
    )
```

## Enable plugin
```python
from maxwelld import vedro_plugin as vedro_maxwell
from maxwelld import ComposeConfig
from env_set import Envs

class Config(vedro.Config):

    class Plugins(vedro.Config.Plugins):
        
        class VedroMaxwell(vedro_maxwell.VedroMaxwell):
            enabled = True
            envs = Envs()
            compose_cfgs = {
                'default': ComposeConfig('docker-compose.yml', parallel_env_limit=1),
                'dev': ComposeConfig('docker-compose.yml:docker-compose.dev.yml', parallel_env_limit=1),
            }
```

## Architecture design
![Architecture design](https://www.plantuml.com/plantuml/proxy?cache=no&src=https://raw.githubusercontent.com/ko10ok/maxwelld/server_split_prototype/ARCH.puml)
