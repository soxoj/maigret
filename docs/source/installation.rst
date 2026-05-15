.. _installation:

Installation
============

Maigret can be installed using pip, Docker, or simply can be launched from the cloned repo.
Also, it is available online via the `community Telegram bot <https://sites.google.com/view/maigret-bot-link>`_,
source code of a bot is `available on GitHub <https://github.com/soxoj/maigret-tg-bot>`_.

Windows Standalone EXE-binaries
-------------------------------

Standalone EXE-binaries for Windows are located in the `Releases section <https://github.com/soxoj/maigret/releases>`_ of GitHub repository.

Currently, the new binary is created automatically after each commit to **main** and **dev** branches.

Video guide on how to run it: https://youtu.be/qIgwTZOmMmM.


Cloud Shells and Jupyter notebooks
----------------------------------

In case you don't want to install Maigret locally, you can use cloud shells and Jupyter notebooks.
Press one of the buttons below and follow the instructions to launch it in your browser.

.. image:: https://user-images.githubusercontent.com/27065646/92304704-8d146d80-ef80-11ea-8c29-0deaabb1c702.png
   :target: https://console.cloud.google.com/cloudshell/open?git_repo=https://github.com/soxoj/maigret&tutorial=README.md
   :alt: Open in Cloud Shell

.. image:: https://replit.com/badge/github/soxoj/maigret
   :target: https://repl.it/github/soxoj/maigret
   :alt: Run on Replit
   :height: 50

.. image:: https://colab.research.google.com/assets/colab-badge.svg
   :target: https://colab.research.google.com/gist/soxoj/879b51bc3b2f8b695abb054090645000/maigret-collab.ipynb
   :alt: Open In Colab
   :height: 45

.. image:: https://mybinder.org/badge_logo.svg
   :target: https://mybinder.org/v2/gist/soxoj/9d65c2f4d3bec5dd25949197ea73cf3a/HEAD
   :alt: Open In Binder
   :height: 45

Local installation from PyPi
----------------------------

Maigret ships with a bundled site database. After installation from PyPI (or any other method), it can **automatically fetch a newer compatible database from GitHub** when you run it—see :ref:`database-auto-update` in :doc:`settings`.

.. note::
   Python 3.10 or higher and pip is required, **Python 3.11 is recommended.**

.. code-block:: bash

   # install from pypi
   pip3 install maigret

   # usage
   maigret username

PDF report support is shipped as an **optional extra** because it relies on
system-level graphics libraries that pip cannot install for you. If you plan to
use ``--pdf``, install Maigret with the ``pdf`` extra:

.. code-block:: bash

   pip3 install 'maigret[pdf]'

See :ref:`pdf-extra` below for the full background on why PDF support is
optional and how to fix the most common build errors.

Development version (GitHub)
----------------------------

.. code-block:: bash

   git clone https://github.com/soxoj/maigret && cd maigret
   pip3 install .

   # OR
   pip3 install git+https://github.com/soxoj/maigret.git

   # usage
   maigret username

   # OR use poetry in case you plan to develop Maigret
   pip3 install poetry
   poetry run maigret

Docker
------

.. code-block:: bash

   # official image of the development version, updated from the github repo
   docker pull soxoj/maigret

   # usage
   docker run -v /mydir:/app/reports soxoj/maigret:latest username --html

   # manual build
   docker build -t maigret .

Troubleshooting
---------------

If you encounter build errors during installation such as ``cannot find ft2build.h``
or errors related to ``reportlab`` / ``_renderPM``, you need to install system-level
dependencies required to compile native extensions.

**Debian/Ubuntu/Kali:**

.. code-block:: bash

   sudo apt install -y libfreetype6-dev libjpeg-dev libffi-dev

**Fedora/RHEL/CentOS:**

.. code-block:: bash

   sudo dnf install -y freetype-devel libjpeg-devel libffi-devel

**Arch Linux:**

.. code-block:: bash

   sudo pacman -S freetype2 libjpeg-turbo libffi

**macOS (Homebrew):**

.. code-block:: bash

   brew install freetype

After installing the system dependencies, retry the maigret installation.

If you continue to have issues, consider using Docker instead, which includes all
necessary dependencies.

.. _pdf-extra:

Optional: PDF reports (``maigret[pdf]``)
----------------------------------------

The ``--pdf`` report format is shipped as an optional extra. To enable it:

.. code-block:: bash

   pip3 install 'maigret[pdf]'

If PDF support is not installed and you pass ``--pdf``, Maigret prints a
warning and continues without crashing — every other output format
(``--html``, ``--json``, ``--csv``, ``--txt``, ``--xmind``, ``--graph``)
keeps working.

Why is PDF optional?
~~~~~~~~~~~~~~~~~~~~

Maigret renders PDFs by converting an HTML template, and that conversion
pipeline ultimately depends on the ``cairo`` graphics library through a
chain of Python packages roughly shaped like::

   maigret[pdf] → xhtml2pdf → svglib → rlPyCairo → pycairo → libcairo2 (system)

The bottom of that chain is a C library — ``libcairo2`` — that has to exist
on the host *before* pip can build the Python bindings. The Python binding
package (``pycairo``) currently ships **only Windows wheels** on PyPI; on
Linux and macOS pip falls back to building from source, and the build fails
the moment ``pkg-config`` cannot find ``cairo``. The error looks like::

   ../cairo/meson.build:31:12: ERROR: Dependency "cairo" not found (tried pkg-config)
   note: This error originates from a subprocess, and is likely not a problem with pip.
   error: metadata-generation-failed

Pulling this whole chain for every Maigret install just so the much smaller
group of users who actually want PDFs can have them is a poor trade — so
``xhtml2pdf`` is gated behind the ``pdf`` extra.

Two more packages — ``arabic-reshaper`` and ``python-bidi`` — are bundled
into the same extra. Maigret core never imports them; they are only used
by ``xhtml2pdf`` to shape Arabic glyphs and lay out right-to-left text in
PDFs. ``python-bidi`` v0.5+ is also a Rust binding, so on niche platforms
without a published wheel it would otherwise pull in a Cargo build for
users who never asked for PDF support.

Installing the system prerequisites
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Install the cairo headers, ``pkg-config``, and a working C toolchain
*before* running ``pip install 'maigret[pdf]'``.

**Debian / Ubuntu / Linux Mint / Kali:**

.. code-block:: bash

   sudo apt update
   sudo apt install -y libcairo2-dev pkg-config python3-dev build-essential
   pip3 install --upgrade pip setuptools wheel
   pip3 install 'maigret[pdf]'

**Fedora / RHEL / CentOS:**

.. code-block:: bash

   sudo dnf install -y cairo-devel pkgconfig python3-devel gcc
   pip3 install 'maigret[pdf]'

**Arch Linux:**

.. code-block:: bash

   sudo pacman -S cairo pkgconf base-devel
   pip3 install 'maigret[pdf]'

**Alpine Linux:**

.. code-block:: bash

   sudo apk add cairo-dev pkgconf python3-dev build-base
   pip3 install 'maigret[pdf]'

**macOS (Homebrew):**

.. code-block:: bash

   brew install cairo pkg-config
   pip3 install --upgrade pip setuptools wheel
   pip3 install 'maigret[pdf]'

**Windows:**

No system packages are needed — ``pycairo`` ships prebuilt wheels for
Windows. Just run:

.. code-block:: bash

   pip install 'maigret[pdf]'

**Google Cloud Shell / Colab / Replit / generic CI:**

These environments behave like Debian/Ubuntu — install the same
``libcairo2-dev pkg-config python3-dev build-essential`` triple before
``pip install 'maigret[pdf]'``. If you do not control the base image and
cannot ``apt install``, skip the extra and use ``--html`` reports instead;
HTML reports contain the same data and open in any browser.

``maigret: command not found`` after install
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If pip prints warnings like::

   WARNING: The scripts maigret and update_sitesmd are installed in
   '/home/<user>/.local/bin' which is not on PATH.

…and ``maigret --version`` then fails with ``command not found``, your
``--user`` install put the entry-point script in a directory the shell does
not search. Add it to ``PATH``:

.. code-block:: bash

   echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
   source ~/.bashrc

Or install into a virtual environment, where the entry point lands in the
venv's ``bin/`` automatically:

.. code-block:: bash

   python3 -m venv ~/.venvs/maigret
   source ~/.venvs/maigret/bin/activate
   pip install 'maigret[pdf]'   # or just `pip install maigret`

Optional: Cloudflare bypass solver
----------------------------------

.. warning::

   **Experimental.** The Cloudflare webgate is under active development;
   the configuration schema and CLI behaviour may change without
   backwards-compatibility guarantees.

Sites tagged ``cf_js_challenge`` / ``cf_firewall`` need a real browser to pass
their JavaScript challenge. To check those sites you can run a local
`FlareSolverr <https://github.com/FlareSolverr/FlareSolverr>`_ instance —
Maigret will route protected checks to it when ``--cloudflare-bypass`` is set:

.. code-block:: bash

   docker run -d -p 8191:8191 --name flaresolverr ghcr.io/flaresolverr/flaresolverr:latest

This is **optional** — Maigret runs without it; only sites whose
``protection`` field intersects ``settings.cloudflare_bypass.trigger_protection``
require the solver. See :ref:`cloudflare-bypass` for details.
