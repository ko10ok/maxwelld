# Maxwell's demon of test enviroment

Orchestrate testing env easily

## Define docker-compose infrastructure
```docker-compose
services:
  app: 
    ...
    
  app-migrations:
    ...
    
  db: 
    ...

  dockersock:
    image: dockersock-expose
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock

  maxwelld:
    image: some/maxwelld
    ports:
      - 9384
    environment:
      - PORT=9384
      - DOCKER_HOST=tcp://dockersock:2375

  e2e:
    ...
    environment:
      - TEST_ENV_CONFIG_HOST=maxwelld  
      - TEST_ENV_CONFIG_PORT=9384    
```

## Wrap with dynamic config
```python
# env.py
from maxweld import testing_config

class Config(Cabina.Config):
    class Moderation(Cabina.Section):
        TOPIC: env.str('KAFKA_TOPIC')
        
config = testing_config(Config()) # overrides ENV values
```

## Setup env presets
```python
# envs.py
from maxwelld import State, env

def migration_script():
    return "exec cmd"

class Envs:
    DEFAULT = BASIC = env(
        service('app', env= maxvelld.from_env_file('.env', filter_in=['field'])),
        service('cli', env= maxvelld.from_env(filter_in=['field'], filter_out=['field']))
    ),
    WITHOUT_MODERATION = env(
        BASIC,
        service('app', env= {'VAR': 'VALUE'})
    },
    WITH_MOCK_MQ = env(
        BASIC,
        service('app', State.UP, env={'VAR': 'VALUE'})  # overwrites BASIC[app][VAR] in BASIC
        service('migrations', State.UP, on_ready=migration_script, env={})
    )
```

## Enable Maxwell's Demon plugin in vedro
```python
# vedro-config.py
from maxweld import MaxwellDConfig
from envs import Envs

class Config(Cabina):
    class MaxwellDConfig(PluginMaxwellD):
        enabled = True
        ens = Envs
```

## Tag test with config setup
```python
# test.py
from maxweld_env import Envs

class Scenario(vedro.Scenario):
    subject='do thing'
    
    tags = [Envs.BASIC]
    ...
```


## Run tests as u wish, don't edit .env and don't restart containers manually
```bash
# vedro --subject="do thing" --maxwelld-verbose
reading configs
reading env:
- app: UP, matched envs
- cli: UP, matched envs
- migrations: sucsessful, done, matched envs
... test steps run and output
```

# Extra 
## Parametrize ur envs
### Setup parametrized env presets
```python
from maxwelld import State, env, session, sibling_run

def topics_script(envs):
    for topic in ['KAFKA_TOPIC', 'ANOTHER_CKAFKA_TOPIC']:
        create_topic(envs['KAFKA_HOST'], topic)  # or do it in tests as KAFKA_TOPIC has session inserted on it via config

class Envs:
    BASIC = env(
        service('app', env=maxvelld.from_env_file('.env', filter_in=['field'])),
        service('cli', env=maxvelld.from_env(filter_in=['field'], filter_out=['field']))
    )
    WITHOUT_MODERATION = env(
        BASIC,
        service('app', env= {'VAR': 'VALUE'})
    )
    WITH_MOCK_MQ = env(
        BASIC,
        service('app', State.UP, session=session, env=topics:={'KAFKA_TOPIC': 'VALUE_$session'}),  # overwrites BASIC[app][KAFKA_TOPIC] in BASIC
        service('kafka', State.UP, Singleton, on_ready=sibling_run('e2e', topics_script), env=topics),
        # or
        # service('kafka', State.External, Singleton, on_ready=sibling_run('e2e', topics_script), env=topics),
    )
```
### Wrapped config returns sessioned vars
```python
> print(config.Kafka.TOPIC)
VALUE_S2452
```

## Parametrisation + Parralelism
If parallelism flag given "-n 10" namespace mode activated by default

```python
from maxwelld import State, env, session, sibling_run

class Envs:
    DEFAULT = BASIC = env(
        service('db', State.SINGLETON, env=maxvelld.from_env(filter_in=['field'], filter_out=['field'])),
        service('migrations', env=db:= {'DATABASE', 'service_$session'}),
        service('kafka', State.SINGLETON, env=kafka:={'HOST': 'kafka:9092', 'TOPIC': 'pictures.$session'}),
        service('app', env=maxvelld.from_env() + db + kafka),
    )
    EXTERNAL_KAFKA = env(
        service('kafka', State.EXTERNAL, env=kafka | {'HOST': 'kafka.external:9092'}),
    )
```

```python
def kafka_topic(name: str = None) -> KafkaTopic:
    name = name or fake(schema.string.alphabetic.length(20))
    return KafkaTopic(f'{config.Kafka.TOPIC}.{name}')
```

```python
class Scenario(vedro.Scenario):
    subject = 'try to run smth and it will use kafka topic'

    tags = [Envs.BASIC]
    
    def given_topic(self):
        self.topic = kafka_topic()
```

Each thread uses his own namespace
```bash
# vedro directory/subdirectory -n 3 --maxwelld-verbose
>> reading configs
>> reading env:
- DB: UP, matched envs
- kafka: UP, matched envs
- migrations_11112: sucsessful, done, matched envs
- migrations_11113: sucsessful, done, matched envs
- migrations_11114: sucsessful, done, matched envs
- app_11112: UP, matched envs
- app_11113: UP, matched envs
- app_11114: UP, matched envs

Scenarios
* directory / subdirectory
 ✔ test1 (11112)
 ✔ test2 (11114)
 ✔ test3 (11113)
 ✔ test4 (11114)
 ✔ test5 (11113)
 ✔ test6 (11112)
 ...
```
