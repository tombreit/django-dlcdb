.PHONY: requirements tests format lint docs

include .env

default_requirements_file = requirements/requirements-dev.txt

help:
	@echo "requirements - check style with black, flake8, sort python with isort, and indent html"
	@echo "format - enforce a consistent code style across the codebase and sort python files with isort"
	@echo "test - run test suite"
	@echo "docs - generate Sphinx HTML documentation, including API docs"

requirements:
	mkdir -p requirements
	pip-compile -o requirements/requirements-prod.txt setup.cfg
	pip-compile --extra ldap -o requirements/requirements-prod-ldap.txt setup.cfg
	pip-compile --extra dev -o requirements/requirements-dev.txt setup.cfg
	ln -s $(default_requirements_file) requirements.txt

tests:
	pytest

format:
	black .
	isort .

lint:
	flake8

docs:
	make -C docs clean
	make -C docs html
