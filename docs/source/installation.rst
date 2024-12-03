.. _installation:

Installation
============

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

Docker
------

.. code-block:: bash

   # official image of the development version, updated from the github repo
   docker pull soxoj/maigret

   # usage
   docker run -v /mydir:/app/reports soxoj/maigret:latest username --html

   # manual build
   docker build -t maigret .
