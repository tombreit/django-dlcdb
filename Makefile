# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: CC0-1.0

.PHONY: requirements tests format lint docs assets messages

# Directories that must never be scanned for translatable strings.
i18n_ignores = --ignore=node_modules --ignore=.venv --ignore=run --ignore=docs --ignore=temp --ignore=frontend

# include .env

default_requirements_file = requirements/prod-ldap.txt

help:
	@echo "requirements - check style with black, flake8, sort python with isort, and indent html"
	@echo "format - enforce a consistent code style across the codebase and sort python files with isort"
	@echo "test - run test suite"
	@echo "docs - generate Sphinx HTML documentation, including API docs"
	@echo "assets - build static assets with npm"
	@echo "messages - extract translatable strings and compile the message catalogs"

requirements:
	mkdir -p requirements
	python3 -m pip install --upgrade pip-tools pip wheel setuptools
	python3 -m piptools compile --upgrade --strip-extras              -o requirements/prod.txt pyproject.toml
	python3 -m piptools compile --upgrade --strip-extras --extra ldap -o requirements/prod-ldap.txt pyproject.toml
	python3 -m piptools compile --upgrade --strip-extras --extra dev  -o requirements/dev.txt pyproject.toml
	ln -s --force  $(default_requirements_file) requirements.txt

tests:
	pytest

# Source strings are English, so only non-English catalogs are maintained.
messages:
	python3 manage.py makemessages -l de $(i18n_ignores)
	@echo "Now translate the empty msgstr entries in dlcdb/locale/de/LC_MESSAGES/django.po, then re-run 'make messages'."
	python3 manage.py compilemessages -l de $(i18n_ignores)

# The mermaid assets are gitignored and only exist once npm has copied them out
# of node_modules. Without them the diagrams render blank, so 'make docs' pulls
# them in itself -- as a file target, so it is a no-op once they are there.
mermaid_assets = docs/_static/vendor/mermaid/mermaid.min.js

$(mermaid_assets):
	@command -v npm >/dev/null 2>&1 || (echo "npm is not installed. Please install npm." && exit 1)
	npm install --loglevel=error
	npm run docs:copy-mermaid --loglevel=error

docs: $(mermaid_assets)
	make --directory=docs clean
	make --directory=docs html

assets:
	@command -v npm >/dev/null 2>&1 || (echo "npm is not installed. Please install npm." && exit 1)
	npm install
	npm run build --loglevel=error
