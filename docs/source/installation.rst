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
