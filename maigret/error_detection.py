from typing import Optional

from maigret import errors
from maigret.errors import CheckError

class ErrorPageDetector:
    def __init__(self,fail_flags=None, ignore_403 = False):
        self.fail_flags = fail_flags or {}
        self.ignore_403 = ignore_403