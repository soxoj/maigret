# Configuration file for the Sphinx documentation builder.

import os

# -- Project information

project = 'Maigret'
copyright = '2025, soxoj'
author = 'soxoj'

release = '0.6.1'
version = '0.6'

# -- Internationalization
#
# Default to English. Translation projects on Read the Docs set the
# ``READTHEDOCS_LANGUAGE`` env var (e.g. ``zh_CN``); locally the language
# can be overridden via ``sphinx-build -D language=zh_CN``.
language = os.environ.get('READTHEDOCS_LANGUAGE', 'en')
locale_dirs = ['locale/']
gettext_compact = False
gettext_uuid = True

# -- General configuration

extensions = [
    'sphinx.ext.duration',
    'sphinx.ext.doctest',
    'sphinx.ext.autodoc',
    'sphinx.ext.autosummary',
    'sphinx.ext.intersphinx',
    'sphinx_copybutton'
]

intersphinx_mapping = {
    'python': ('https://docs.python.org/3/', None),
    'sphinx': ('https://www.sphinx-doc.org/en/master/', None),
}
intersphinx_disabled_domains = ['std']

templates_path = ['_templates']

# -- Options for HTML output

html_theme = 'sphinx_rtd_theme'

# -- Options for EPUB output
epub_show_urls = 'footnote'
