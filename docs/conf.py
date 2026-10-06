import os
import sys

import django
from django.conf import settings

sys.path.insert(0, os.path.abspath(".."))

# # Add node_modules/.bin path to path. Only used for mermaid cli atm.
# node_bin_path = os.path.abspath('../node_modules/.bin')
# sys.path.append(node_bin_path)

# Without a .env (GitHub Pages, the wheel build), base falls back to its
# production defaults.
os.environ["DJANGO_SETTINGS_MODULE"] = "dlcdb.settings.base"
django.setup()


# Generate the OpenAPI schema from drf-spectacular at build time, so the API
# reference in docs/betrieb/api.md can never drift from the code. The file is
# gitignored (see .gitignore) and regenerated on every sphinx-build, both
# locally and on GitHub (.github/workflows/docs.yml).
from django.core.management import call_command

_schema_path = os.path.join(os.path.dirname(__file__), "_generated", "openapi.yaml")
os.makedirs(os.path.dirname(_schema_path), exist_ok=True)
call_command("spectacular", file=_schema_path, validate=True)


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
    "sphinxcontrib.openapi",
    # 'sphinx.ext.autosectionlabel',  # sphinx WARNING: duplicate label foo other instance in bar
    "myst_parser",
    "sphinx_design",
    # 'linkify',
    "sphinx_togglebutton",
]

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

# Language to be used for generating the HTML full-text search index.
# Sphinx supports the following languages:
#   'da', 'de', 'en', 'es', 'fi', 'fr', 'h', 'it', 'ja'
#   'nl', 'no', 'pt', 'ro', 'r', 'sv', 'tr', 'zh'
#
# html_search_language = 'en'

html_css_files = [
    "css/custom.css",
]

html_js_files = [
    "vendor/mermaid/mermaid.min.js",
]

html_theme = "pydata_sphinx_theme"
html_static_path = ["_static"]


# Upstream defaults on purpose: top navigation from the root toctree, section
# sidebar on the left, page TOC on the right.
html_title = "DLCDB"

html_theme_options = {
    "github_url": "https://github.com/tombreit/django-dlcdb",
    # The app's figurative mark, one file per color mode; the theme copies them
    # to _static. With an image, the title text shows only when set here.
    "logo": {
        "image_light": "../dlcdb/theme/static/theme/branding/dlcdb_mark_light.svg",
        "image_dark": "../dlcdb/theme/static/theme/branding/dlcdb_mark_dark.svg",
        "text": html_title,
    },
}

# Top-level pages without subpages would show an empty section sidebar.
html_sidebars = {
    "konzept": [],
    "faq": [],
}

# html_favicon = "path/to/favicon.ico"

base_url = settings.DLCDB_BASE_URL
myst_substitutions = {
    "base_url": base_url,
    "licenses_fe_link": f"[Lizenzen]({base_url}/licenses/)",
    "inventorize_fe_link": f"[Inventarisieren]({base_url}/inventory/)",
    "devices_fe_link": f"[Geräte]({base_url}/assets/devices/)",
    "api_base_url": f"[{base_url}/api/v2/]({base_url}/api/v2/)",
    "api_swagger_url": f"[{base_url}/api/v2/schema/swagger-ui/]({base_url}/api/v2/schema/swagger-ui/)",
}
myst_enable_extensions = ["colon_fence", "substitution", "attrs_inline", "html_image"]
myst_heading_anchors = 6

# https://github.com/mgaitan/sphinxcontrib-mermaid#directive-options
#
# All assets come from docs/_static/vendor/mermaid/, populated by
# `npm run docs:copy-mermaid` -- the built pages must not reach out to a CDN.
# The option is named d3_use_local (not mermaid_d3_use_local); with the wrong
# name it is silently ignored and the extension falls back to jsdelivr.
# d3 is only used for the optional zoom feature, but sphinxcontrib-mermaid adds
# the script unconditionally, so it has to be served locally either way.
d3_use_local = "vendor/mermaid/d3.min.js"
#
# Diagrams are rendered by the plain <script> in html_js_files above, which is
# the IIFE build (it assigns globalThis.mermaid). mermaid_use_local must still
# point at a local file: left unset, the extension's own ES-module loader would
# import mermaid from jsdelivr. That loader stays inert either way -- it wants
# mermaid.esm.min.mjs plus its chunks/, which docs:copy-mermaid does not vendor.
mermaid_use_local = "vendor/mermaid/mermaid.min.js"
