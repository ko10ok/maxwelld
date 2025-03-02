FROM docker:25.0.3-dind-alpine3.19

FROM alpine:3.19
COPY --from=docker:25.0.3-dind-alpine3.19 /usr/local/bin/docker /usr/local/bin/
LABEL description="Maxwelld (http://github.com/ko10ok/maxwelld) service. \
Env params should be set up: \
- COMPOSE_PROJECT_NAME - compose project name (namespace); \
- DEFAULT_COMPOSE_FILES - compose project files used by default; \
- HOST_PROJECT_ROOT_DIRECTORY - path for services volumes mapping; \
- HOST_TMP_ENV_DIRECTORY - volumed path for temporarely generated envs; \
- DOCKER_HOST - docker service host; \
- PORT - service port (default=80); \
- TMP_ENVS_DIRECTORY (default=/env-tmp) - tmp compose files directory; \
- PROJECT_ROOT_DIRECTORY (default=/project ) - volume with project root when project contains service with volumes"

WORKDIR /maxwelld

ARG TARGETPLATFORM

ENV PROJECT_ROOT_DIRECTORY=${PROJECT_ROOT_DIRECTORY:-"/project"}
ENV TMP_ENVS_DIRECTORY=${TMP_ENVS_DIRECTORY:-"/tmp-envs"}
ENV TMP_ENVS_REGISTER_FILE=${TMP_ENVS_REGISTER_FILE:-"envs.json"}

RUN echo "alias dc='docker-compose'" >> /root/.bashrc

RUN apk add --no-cache python3 py-pip curl
RUN python3 -m venv /venv

RUN /venv/bin/python3 -m pip install --upgrade pip

ADD ./requirements.txt .
RUN /venv/bin/python3 -m pip install -r requirements.txt

RUN if [[ "$TARGETPLATFORM" = "linux/amd64" ]] ; then curl -SL https://github.com/docker/compose/releases/download/v2.24.4/docker-compose-linux-x86_64 -o /usr/local/bin/docker-compose ; fi
RUN if [[ "$TARGETPLATFORM" = "linux/arm64" ]] ; then curl -SL https://github.com/docker/compose/releases/download/v2.24.4/docker-compose-linux-aarch64 -o /usr/local/bin/docker-compose ; fi

RUN chmod +x /usr/local/bin/docker-compose

ADD . .
RUN /venv/bin/python3 -m pip install .

CMD ["/venv/bin/python3", "-m", "maxwelld"]
