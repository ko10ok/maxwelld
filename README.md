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

# How To Start Contributing

## Run e2e tests
```bash
cd tests
make watch  # separate terminal to watch for changes
make e2e-run

# verbose output 
make e2e-run args='-vvv'

# specific test
make e2e-run args='scenarios/api/up_env_with_custom_services_set_enviroment.py -vvv'
```

## Update in-image maxwelld library / rebuild dependencies
```bash
make watch -B  # kill & restart existing watcher
# or
make e2e-run -B  # rebuild before test run
```

## Run in-project integrated
### Client changes testing (e2e vedro) 
Add volume with package
```yaml
  e2e:
    volumes:
      - /Users/***/repos/maxwelld:/maxwelld
```
and update in started container
```bash
docker-compose exec e2e /venv/bin/python3 -m pip install /maxwelld
```

### Server changes testing
make beta image
```bash
make build-image-beta
```
and change it for ur project
```yaml
    image: docker.io/***/maxwelld:*.*.*-beta
```
