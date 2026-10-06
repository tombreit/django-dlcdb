# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: CC0-1.0

.PHONY: requirements tests format lint docs assets messages check-version wheel release

# include .env

default_requirements_file = requirements/prod-ldap.txt

help:
	@echo "requirements - check style with black, flake8, sort python with isort, and indent html"
	@echo "format - enforce a consistent code style across the codebase and sort python files with isort"
	@echo "test - run test suite"
	@echo "docs - generate Sphinx HTML documentation, including API docs"
	@echo "assets - build static assets with npm"
	@echo "messages - extract translatable strings and compile the message catalogs"
	@echo "wheel - build the wheel from HEAD in run/release/ and try it in a fresh venv"
	@echo "release VERSION=X.Y.Z - set the version everywhere, then build and try the wheel"

requirements:
	mkdir -p requirements
	python3 -m pip install --upgrade pip-tools pip wheel setuptools
	python3 -m piptools compile --upgrade --strip-extras --extra docs              -o requirements/prod.txt pyproject.toml
	python3 -m piptools compile --upgrade --strip-extras --extra docs --extra ldap -o requirements/prod-ldap.txt pyproject.toml
	python3 -m piptools compile --upgrade --strip-extras --extra docs --extra dev  -o requirements/dev.txt pyproject.toml
	python3 -m piptools compile --upgrade --strip-extras --extra docs --extra ldap --extra container -o requirements/container.txt pyproject.toml
	ln -s --force  $(default_requirements_file) requirements.txt

tests:
	pytest

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

# Releases (see docs/betrieb/development.md, section Release). Run them in the
# activated dev venv: the build needs Django, Sphinx and `build`.
release_dir = run/release
REF ?= HEAD
SMOKE_PYTHON ?= python3
version = $(shell python3 -c "import dlcdb; print(dlcdb.__version__)")
npm_version = $(shell node -p "require('./package.json').version")

# The version lives in dlcdb/__init__.py and, by hand, in package.json; with
# TAG=vX.Y.Z (the release workflow) the tag must match it as well.
check-version:
	@test "$(version)" = "$(npm_version)" || (echo "dlcdb/__init__.py says $(version), package.json $(npm_version)" && exit 1)
	@test -z "$(TAG)" || test "$(TAG)" = "v$(version)" || (echo "Tag $(TAG) does not match version $(version)" && exit 1)

# Builds the wheel from a commit (REF, default HEAD) in a fresh run/release/,
# never in the working tree: setuptools leaves build/ and *.egg-info/ behind,
# and the wheel needs the gitignored frontend bundles, docs and collected static
# files copied into the package. Then installs it into a fresh venv and tries it.
wheel: check-version
	@test "$(REF)" != HEAD || git diff --quiet HEAD || echo "Note: uncommitted changes are not part of the wheel"
	rm -rf $(release_dir)
	mkdir -p $(release_dir)/src
	git archive $(REF) | tar -x -C $(release_dir)/src
	cd $(release_dir)/src && npm ci --loglevel=error && npm run build --loglevel=error
	$(MAKE) --directory=$(release_dir)/src docs
	cd $(release_dir)/src && python3 manage.py collectstatic --noinput
	cd $(release_dir)/src && cp -r run/docs/html dlcdb/docs_html && cp -r run/staticfiles dlcdb/staticfiles
	cd $(release_dir)/src && python3 -m build --wheel --outdir ../dist
	$(SMOKE_PYTHON) -m venv $(release_dir)/venv
	$(release_dir)/venv/bin/pip install --quiet $(release_dir)/dist/*.whl
	mkdir $(release_dir)/instance
	# Not from here: `python -m` would import dlcdb from the checkout, not from the wheel
	cd $(release_dir)/instance && DLCDB_HOME=$$PWD ../venv/bin/python -m dlcdb dlcdb_init
	cd $(release_dir)/instance && ./manage.py check && ./manage.py migrate --noinput --verbosity 0
	cd $(release_dir)/instance && ./manage.py shell --verbosity 0 --command \
		"from django.test import Client; assert Client().get('/accounts/login/', HTTP_HOST='127.0.0.1').status_code == 200"
	@echo "Wheel: $$(ls $(release_dir)/dist/*.whl)"

# Prepares release VERSION=X.Y.Z: writes the version to all three places, then
# builds and tries the wheel from exactly that state (the committed tree plus
# the version change, via `git stash create`). Commit, tag and push stay yours.
release:
	@echo "$(VERSION)" | grep -Eq '^[0-9]+\.[0-9]+\.[0-9]+$$' || (echo "Usage: make release VERSION=X.Y.Z" && exit 1)
	@test -z "$$(git status --porcelain)" || (echo "Commit or stash your changes first: a release is the committed state" && exit 1)
	@! git rev-parse --quiet --verify refs/tags/v$(VERSION) >/dev/null || (echo "Tag v$(VERSION) exists already" && exit 1)
	sed -i 's/^__version__ = ".*"/__version__ = "$(VERSION)"/' dlcdb/__init__.py
	npm version $(VERSION) --no-git-tag-version --allow-same-version --loglevel=error
	ref=$$(git stash create) && $(MAKE) --no-print-directory wheel REF=$${ref:-HEAD}
	@echo "Next: git commit --all --message \"Version $(VERSION)\" && git tag v$(VERSION) && git push <github-remote> HEAD v$(VERSION)"
