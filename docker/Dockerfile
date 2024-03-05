FROM docker:25.0.3-dind-alpine3.19

FROM alpine:3.19
COPY --from=docker:25.0.3-dind-alpine3.19 /usr/local/bin/docker /usr/local/bin/
LABEL description="Maxwelld (http://github.com/ko10ok/maxwelld) service\
\
Env params should be set up:\
- COMPOSE_PROJECT_NAME - compose project name (namespace)\
- COMPOSE_FILES_DIRECTORY - compose files directory\
- PROJECT_ROOT_DIRECTORY - volume with project root when project contains service with volumes\
- HOST_PROJECT_ROOT_DIRECTORY - path for services volumes mapping\
- HOST_TMP_ENV_DIRECTORY - volumed path for temporarely generated envs \
- DOCKER_HOST - docker service (or docker.sock)\
- PORT - service port (80 by default)"

WORKDIR /maxwelld

ARG TARGETPLATFORM

RUN apk add --no-cache python3 py-pip curl
RUN python3 -m venv venv

ADD requirements.txt .
RUN venv/bin/python3 -m pip install --upgrade pip
RUN venv/bin/python3 -m pip install -r requirements.txt

RUN if [[ "$TARGETPLATFORM" = "linux/amd64" ]] ; then curl -SL https://github.com/docker/compose/releases/download/v2.24.4/docker-compose-linux-x86_64 -o /usr/local/bin/docker-compose ; fi
RUN if [[ "$TARGETPLATFORM" = "linux/arm64" ]] ; then curl -SL https://github.com/docker/compose/releases/download/v2.24.4/docker-compose-linux-aarch64 -o /usr/local/bin/docker-compose ; fi

RUN chmod +x /usr/local/bin/docker-compose

CMD ["venv/bin/python3", "-m", "maxwelld"]
