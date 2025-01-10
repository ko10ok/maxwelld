export COMPOSE_FILE ?= docker-compose.yml:docker-compose.dev.yml
export VERSION=$(shell cat ../maxwelld/version)

.PHONY: down
down:
	rm up || true
	rm dep || true
	docker-compose down || true

up:
	docker-compose up -d
	echo "" > up

deps: up
	docker-compose exec ${CI_DC_DISABLE_TTY} e2e python3 -m venv /venv
	docker-compose exec ${CI_DC_DISABLE_TTY} e2e /venv/bin/python3 -m pip install --upgrade pip
	docker-compose exec ${CI_DC_DISABLE_TTY} e2e /venv/bin/python3 -m pip install -r requirements.txt
	docker-compose exec ${CI_DC_DISABLE_TTY} e2e /venv/bin/python3 -m pip install /maxwelld
	echo "" > deps

.PHONY: e2e-run
e2e-run: up deps
	docker-compose exec ${CI_DC_DISABLE_TTY} e2e /venv/bin/python3 -m vedro run $(args)

.PHONY: watch
watch: up deps
	docker-compose watch maxwelld --no-up
