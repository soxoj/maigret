.. _installation:

Installation
============

Maigret can be installed using pip, Docker, or simply can be launched from the cloned repo.
Also, it is available online via `official Telegram bot <https://t.me/osint_maigret_bot>`_,
source code of a bot is `available on GitHub <https://github.com/soxoj/maigret-tg-bot>`_.

Package installing
------------------

Please note that the sites database in the PyPI package may be outdated.
If you encounter frequent false positive results, we recommend installing the latest development version from GitHub instead.

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

Cloud shells and Jupyter notebooks
----------------------------------

In case you don't want to install Maigret locally, you can use cloud shells and Jupyter notebooks.

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

Windows standalone EXE-binaries
-------------------------------

Standalone EXE-binaries for Windows are located in the `Releases section <https://github.com/soxoj/maigret/releases>`_ of GitHub repository.

Currently, the new binary is created automatically after each commit to the main branch, but is not deployed to the Releases section automatically.

Docker
------

.. code-block:: bash

   # official image of the development version, updated from the github repo
   docker pull soxoj/maigret

   # usage
   docker run -v /mydir:/app/reports soxoj/maigret:latest username --html

   # manual build
   docker build -t maigret .
