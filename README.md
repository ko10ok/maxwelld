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
```plantuml

participant "Maxwell(Tests)"


box Maxwell's Demon Container #lightblue
participant "Maxwell's Demon"


== Initialize startup of env ==

"Maxwell(Tests)" -> "Maxwell's Demon" : up(id=123)
note right
{
    << compose_files >>
    << parallelism >> //  == 1?  ->  id=no_id
}
end note 
activate "Maxwell's Demon"
"Maxwell(Tests)" <-- "Maxwell's Demon" : ENV && << task scheduled >>

"Maxwell's Demon" -> "docker-compose(prefix=123)" ** : 
"Maxwell's Demon" -> "docker-compose(prefix=123)": up -d COMPOSE_FILE=<< compose_files >>
activate "docker-compose(prefix=123)"


== Env state polling ==

"Maxwell(Tests)" -> "Maxwell's Demon" : get_status(id=123)
activate "Maxwell's Demon"

"Maxwell's Demon" -> "docker-compose(prefix=123)" : dc ps -a format=={{json .}}
"Maxwell's Demon" <-- "docker-compose(prefix=123)" : [ {service:status}, ... ]

return status (=ask_later)

note right
"up" procedure can be finished anytime
end note


"Maxwell's Demon" -> "docker-compose(prefix=123)": dc exec %service% hooks/migrations

"Maxwell's Demon" <-- "docker-compose(prefix=123)"
deactivate "Maxwell's Demon"


"Maxwell(Tests)" -> "Maxwell's Demon" : get_status(id=123)
activate "Maxwell's Demon"

"Maxwell's Demon" -> "docker-compose(prefix=123)" : dc ps -a format=={{json .}}
"Maxwell's Demon" <-- "docker-compose(prefix=123)" : [ {service:status}, ... ]

return status{services}
```
