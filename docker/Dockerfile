FROM docker:25.0.3-dind-alpine3.19

FROM alpine:3.19
COPY --from=docker:25.0.3-dind-alpine3.19 /usr/local/bin/docker /usr/local/bin/
LABEL description="Maxwelld (http://github.com/ko10ok/maxwelld) service. \
Env params should be set up: \
- COMPOSE_PROJECT_NAME - compose project name (namespace); \
- HOST_PROJECT_ROOT_DIRECTORY - path for services volumes mapping; \
- HOST_TMP_ENV_DIRECTORY - volumed path for temporarely generated envs; \
- DOCKER_HOST - docker service host; \
- PORT - service port (default=80); \
- COMPOSE_FILES_DIRECTORY (default=/docker-composes) - compose files directory; \
- TMP_ENVS_DIRECTORY (default=/env-tmp) - tmp compose files directory; \
- PROJECT_ROOT_DIRECTORY (default=/project ) - volume with project root when project contains service with volumes"

WORKDIR /maxwelld

ARG TARGETPLATFORM

ENV COMPOSE_FILES_DIRECTORY=${COMPOSE_FILES_DIRECTORY:-"/docker-composes"}
ENV PROJECT_ROOT_DIRECTORY=${PROJECT_ROOT_DIRECTORY:-"/project"}
ENV TMP_ENVS_DIRECTORY=${TMP_ENVS_DIRECTORY:-"/env-tmp"}
ENV TMP_ENVS_REGISTER_FILE=${TMP_ENVS_REGISTER_FILE:-"envs.json"}

RUN mkdir "$TMP_ENVS_DIRECTORY"

RUN apk add --no-cache python3 py-pip curl
RUN python3 -m venv venv

RUN venv/bin/python3 -m pip install --upgrade pip

ADD ./requirements.txt .
RUN venv/bin/python3 -m pip install -r requirements.txt

ADD . maxwelld-lib
RUN venv/bin/python3 -m pip install ./maxwelld-lib

RUN if [[ "$TARGETPLATFORM" = "linux/amd64" ]] ; then curl -SL https://github.com/docker/compose/releases/download/v2.24.4/docker-compose-linux-x86_64 -o /usr/local/bin/docker-compose ; fi
RUN if [[ "$TARGETPLATFORM" = "linux/arm64" ]] ; then curl -SL https://github.com/docker/compose/releases/download/v2.24.4/docker-compose-linux-aarch64 -o /usr/local/bin/docker-compose ; fi

RUN chmod +x /usr/local/bin/docker-compose

CMD ["venv/bin/python3", "-m", "maxwelld"]
