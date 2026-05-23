# Minimal makefile for Sphinx documentation
#

# You can set these variables from the command line, and also
# from the environment for the first two.
SPHINXOPTS    ?=
SPHINXBUILD   ?= sphinx-build
SOURCEDIR     = source
BUILDDIR      = build

# Put it first so that "make" without argument is like "make help".
help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

.PHONY: help Makefile gettext intl-update html-zh_CN

# Translation pipeline
#
# 1. `make gettext` regenerates .pot files from the English .rst sources.
# 2. `make intl-update LANG=zh_CN` syncs the .po files for that language
#    against the new .pot files (new strings get empty msgstrs, removed
#    strings get commented out, changed strings get a `fuzzy` marker).
# 3. `make html-zh_CN` builds a local Simplified Chinese HTML preview.
#
# To bootstrap a new language, run `make intl-update LANG=<code>`.
LANG ?= zh_CN

gettext:
	$(SPHINXBUILD) -b gettext $(SPHINXOPTS) "$(SOURCEDIR)" "$(BUILDDIR)/gettext"

intl-update: gettext
	sphinx-intl update -p "$(BUILDDIR)/gettext" -l $(LANG) -d "$(SOURCEDIR)/locale"

html-zh_CN:
	$(SPHINXBUILD) -b html -D language=zh_CN $(SPHINXOPTS) "$(SOURCEDIR)" "$(BUILDDIR)/html_zh_CN"

# Catch-all target: route all unknown targets to Sphinx using the new
# "make mode" option.  $(O) is meant as a shortcut for $(SPHINXOPTS).
%: Makefile
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)
