# Maxwell's demon of test enviroment

Orchestrate testing env easily

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

class Config(vedro.Config):

    class Plugins(vedro.Config.Plugins):
        
        class VedroMaxwell(vedro_maxwell.VedroMaxwell):
            enabled = True
            envs = Envs()
            compose_cfgs = {
                'default': ComposeConfig(os.environ.get('DC_FILES'), parallel_env_limit=1),
                'dev': ComposeConfig(os.environ.get(f'DC_FILES_1'), parallel_env_limit=1),
            }
```

## Architecture design
![Architecture design](https://www.plantuml.com/plantuml/proxy?cache=no&src=https://raw.githubusercontent.com/ko10ok/maxwelld/server_split_prototype/ARCH.puml)
