#!/usr/bin/env python3

import os
import sys
import django


sys.path.insert(0, os.path.abspath(".."))

# # Add node_modules/.bin path to path. Only used for mermaid cli atm.
# node_bin_path = os.path.abspath('../node_modules/.bin')
# sys.path.append(node_bin_path)

# A minimal .env with production settings is created for gitlab pages
# see .gitlab.ci.yml
os.environ["DJANGO_SETTINGS_MODULE"] = "dlcdb.settings.base"
django.setup()


# -- Expose UDB settings ----------------------------------------------

# Expose django settings in Sphinx MyST doc as substitution vars
# Usage in docs:
# ```md
# Debug Mode: {sub}`debug_mode`
# ```
# TODO:
# * Do not expose sensible data (eg. passwords)
# * Get base url/fqdn of instance

# import environ
# from django.conf import settings

# env = environ.Env(
#     SETTINGS_MODE=(str, "dev"),
#     DJANGO_DEBUG=(bool, True),
#     AUTH_LDAP=(bool, False),
#     SECRET_KEY=(str, "!set-your-secretkey-via-dot-env-file!"),
#     ADMINS=(str, ""),
# )
# environ.Env.read_env(settings.BASE_DIR / ".env")

# myst_substitutions_django_settings = {}

# serialized_setting_types = [
#     str,
#     bool,
#     int,
# ]

# for setting in dir(settings):
#     if setting.isupper():
#         value = getattr(settings, setting)
#         if type(value) in serialized_setting_types:
#             myst_substitutions_django_settings.update({
#                 setting: value
#             })

# myst_substitutions = myst_substitutions_django_settings

# -- General configuration ------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.todo",
    "sphinx.ext.coverage",
    "sphinx.ext.viewcode",
    "sphinxcontrib.mermaid",
    # 'sphinx.ext.autosectionlabel',  # sphinx WARNING: duplicate label foo other instance in bar
    "myst_parser",
    "sphinx_design",
    # 'linkify',
]

autosectionlabel_prefix_document = True
autosectionlabel_maxdepth = 1

templates_path = ["_templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# The suffix(es) of source filenames.
# You can specify multiple suffix as a list of string:
#
source_suffix = [".rst", ".md"]

# The master toctree document.
master_doc = "index"

# General information about the project.
project = "DLCDB"
copyright = "2022, Thomas Breitner"
author = "Thomas Breitner"

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
# version = '1.0'

# The full version, including alpha/beta/rc tags.
# release = '0'

language = "de"

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = "sphinx"

# If true, `todo` and `todoList` produce output, else they produce nothing.
todo_include_todos = True

# -- Options for HTML output ----------------------------------------------

html_css_files = [
    "css/custom.css",
]

html_js_files = [
    "vendor/mermaid/mermaid.min.js",
]

html_theme = "sphinx_book_theme"
html_static_path = ["_static"]


html_theme_options = {
    "repository_url": "https://gitlab.gwdg.de/t.breitner/django-dlcdb",
    "use_repository_button": True,
    "show_toc_level": 3,
    "navigation_with_keys": True,
    "extra_footer": '<p>Questions?<br><a href="mailto:t.breitner@csl.mpg.de">📧 Thomas Breitner</a></p>',
}

html_title = "♻ DLCDB Docs"
# html_logo = "path/to/logo.png"
# html_favicon = "path/to/favicon.ico"


# Language to be used for generating the HTML full-text search index.
# Sphinx supports the following languages:
#   'da', 'de', 'en', 'es', 'fi', 'fr', 'h', 'it', 'ja'
#   'nl', 'no', 'pt', 'ro', 'r', 'sv', 'tr', 'zh'
#
# html_search_language = 'en'


# https://github.com/mgaitan/sphinxcontrib-mermaid#directive-options
# Use local hosted version for mermaid.js; see html_js_files
# Using sphinxconrib-mermaid<1.0.0, because 1.0.0 yields the following error:
# Extension error (sphinxcontrib.mermaid):
# Handler <function install_js at 0x7f9286281e40> for event 'html-page-context' threw an exception (exception: Invalid version: '')
mermaid_version = ""


myst_enable_extensions = ["colon_fence"]
myst_heading_anchors = 6
