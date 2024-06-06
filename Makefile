export VERSION=$(shell cat maxwelld/version)

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
	docker build -f docker/Dockerfile . -t ko10ok/maxwelld:${VERSION}

.PHONY: push-image
push-image:
	docker push ko10ok/maxwelld:${VERSION}

.PHONY: buildx-build-n-push-image
buildx-build-n-push-image:
	docker buildx build --platform linux/amd64,linux/arm64 -f docker/Dockerfile . -t ko10ok/maxwelld:${VERSION} --push

.PHONY: buildx-builder
buildx-builder:
	docker buildx ls
	docker buildx create --driver docker-container --name maxwelld-builder || true
	docker buildx use --builder maxwelld-builder

.PHONY: build-image-beta
build-image-beta:
	echo "Building version: ${VERSION}"
	docker build -f docker/Dockerfile . -t ko10ok/maxwelld:${VERSION}-beta

.PHONY: push-image-beta
push-image-beta:
	docker push ko10ok/maxwelld:${VERSION}-beta

.PHONY: tag
tag:
	git tag v${VERSION}
