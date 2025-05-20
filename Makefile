# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: CC0-1.0

.PHONY: requirements tests format lint docs assets

# include .env

default_requirements_file = requirements/prod-ldap.txt

help:
	@echo "requirements - check style with black, flake8, sort python with isort, and indent html"
	@echo "format - enforce a consistent code style across the codebase and sort python files with isort"
	@echo "test - run test suite"
	@echo "docs - generate Sphinx HTML documentation, including API docs"
	@echo "assets - build static assets with npm"

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

assets:
	@command -v npm >/dev/null 2>&1 || (echo "npm is not installed. Please install npm." && exit 1)
	npm install
	npm run build --loglevel=error