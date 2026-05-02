"""Maigret"""

__title__ = 'Maigret'
__package__ = 'maigret'
__author__ = 'Soxoj'
__author_email__ = 'soxoj@protonmail.com'


from .__version__ import __version__
try:
    from .checking import maigret as search
except ImportError as e:
    raise ImportError(
        "Missing required dependency while starting Maigret.\n\n"
        "If installed from PyPI:\n"
        "    pip install -U maigret\n\n"
        "If running from a cloned repository:\n"
        "    pip install -e .\n\n"
        "Then run Maigret as:\n"
        "    python -m maigret <username>"
    ) from e
from .maigret import main as cli
from .sites import MaigretEngine, MaigretSite, MaigretDatabase
from .notify import QueryNotifyPrint as Notifier
