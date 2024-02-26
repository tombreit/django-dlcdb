.PHONY: requirements tests format lint docs

# include .env

default_requirements_file = requirements/prod-ldap.txt

help:
	@echo "requirements - check style with black, flake8, sort python with isort, and indent html"
	@echo "format - enforce a consistent code style across the codebase and sort python files with isort"
	@echo "test - run test suite"
	@echo "docs - generate Sphinx HTML documentation, including API docs"

requirements:
	mkdir -p requirements
	python3 -m pip install --upgrade pip-tools pip wheel setuptools
	python3 -m piptools compile --upgrade --strip-extras              -o requirements/prod.txt pyproject.toml
	python3 -m piptools compile --upgrade --strip-extras --extra ldap -o requirements/prod-ldap.txt pyproject.toml
	python3 -m piptools compile --upgrade --strip-extras --extra dev  -o requirements/dev.txt pyproject.toml
	ln -s --force  $(default_requirements_file) requirements.txt

tests:
	pytest

docs:
	make --directory=docs clean
	make --directory=docs html
