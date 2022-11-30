#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import django
from django.conf import settings

sys.path.insert(0, os.path.abspath(".."))

# # Add node_modules/.bin path to path. Only used for mermaid cli atm.
# node_bin_path = os.path.abspath('../node_modules/.bin')
# sys.path.append(node_bin_path)
os.environ['DJANGO_SETTINGS_MODULE'] = 'dlcdb.settings.base'

# settings.configure(
#     DEBUG=False,
# )

# FIXME Do not alter settings at runtime
# https://docs.djangoproject.com/en/4.1/topics/settings/#altering-settings-at-runtime
settings.DEBUG = False
django.setup()


# -- General configuration ------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.todo',
    'sphinx.ext.coverage',
    'sphinx.ext.viewcode',
    'sphinxcontrib.mermaid',
    # 'sphinx.ext.autosectionlabel',  # sphinx WARNING: duplicate label foo other instance in bar
    'myst_parser',
    'sphinx_design',
    # 'linkify',
]

autosectionlabel_prefix_document = True
autosectionlabel_maxdepth = 1

templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

# The suffix(es) of source filenames.
# You can specify multiple suffix as a list of string:
#
source_suffix = ['.rst', '.md']

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = 'DLCDB'
copyright = '2022, Thomas Breitner'
author = 'Thomas Breitner'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
#version = '1.0'

# The full version, including alpha/beta/rc tags.
#release = '0'

language = "de"

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# If true, `todo` and `todoList` produce output, else they produce nothing.
todo_include_todos = True

# -- Options for HTML output ----------------------------------------------

# https://github.com/mgaitan/sphinxcontrib-mermaid#directive-options
# Use local hosted version for mermaid.js; see html_js_files
mermaid_version = ""

html_theme = "sphinx_book_theme"
html_static_path = ['_static']

html_css_files = [
    'css/custom.css',
]

html_js_files = [
   'vendor/mermaid/mermaid.min.js',
]

html_theme_options = {
    "repository_url": "https://gitlab.gwdg.de/t.breitner/django-dlcdb",
    "use_repository_button": True,
    "show_toc_level": 3,
    "extra_navbar": '<p>Questions?<br><a href="mailto:t.breitner@csl.mpg.de">📧 Thomas Breitner</a></p>',
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

myst_enable_extensions = ["colon_fence"]
myst_heading_anchors = 6
