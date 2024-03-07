PROJECT_NAME=vedro_interactive

.PHONY: install-deps
install-deps:
	pip3 install --quiet --upgrade pip
	pip3 install --quiet -r requirements.txt

.PHONY: install-local
install-local: install-deps
	pip3 install . --force-reinstall

.PHONY: build
build:
	pip3 install --quiet --upgrade pip
	pip3 install --quiet --upgrade setuptools wheel twine
	python3 setup.py sdist bdist_wheel

.PHONY: publish
publish:
	twine upload dist/*

.PHONY: build-image
build-image:
	echo maxwelld==`cat maxwelld/version` > docker/requirements.txt
	docker build -f docker/Dockerfile . -t ko10ok/maxwelld:`cat maxwelld/version`

.PHONY: push-image
push-image:
	docker push ko10ok/maxwelld:`cat maxwelld/version`

.PHONY: build-n-push-beta-image
build-n-push-beta-image:
	echo maxwelld==`cat maxwelld/version` > docker/requirements.txt
	docker build -f docker/Dockerfile . -t ko10ok/maxwelld:`cat maxwelld/version`-beta
	docker push ko10ok/maxwelld:`cat maxwelld/version`-beta
