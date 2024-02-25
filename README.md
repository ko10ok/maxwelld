# Maxwell's demon of test enviroment

Orchestrate testing env easily

# Install & activate
## Install package
```shell
$ pip3 install maxwelld
```

## Define services config
```python
from maxwelld import Environments
from maxwelld import Environment
from maxwelld import DEFAULT_ENV

class Envs(Environments):
    DEFAULT = Environment(
        DEFAULT_ENV,
        builder, web, web_gallery, wep_ext_app, cli,
        db,
        mq,
        e2e
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
                'default': ComposeConfig(os.environ.get('DC_FILES')),
                'dev': ComposeConfig(os.environ.get(f'DC_FILES_1'), parallel_env_limit=1),
            }
            project = os.environ.get('COMPOSE_PROJECT_NAME', default='some_project')
```

## Architecture design draft
![Architecture design draft](http://www.plantuml.com/plantuml/proxy?cache=no&src=https://raw.githubusercontent.com/ko10ok/maxwelld/server_split_prototype/ARCH.puml)
