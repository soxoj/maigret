"""Maigret"""

__title__ = 'Maigret'
__package__ = 'maigret'
__author__ = 'Soxoj'
__author_email__ = 'soxoj@protonmail.com'


from .__version__ import __version__
from .checking import maigret as search
from .sites import MaigretEngine, MaigretSite, MaigretDatabase
from .notify import QueryNotifyPrint as Notifier
