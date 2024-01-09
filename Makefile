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
