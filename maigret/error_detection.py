from typing import Dict, Optional

from maigret import errors
from maigret.errors import CheckError


def detect_error_page(
    html_text: str,
    status_code: int,
    fail_flags: Optional[Dict[str, str]] = None,
    ignore_403: bool = False,
) -> Optional[CheckError]:
    """Classify a response as an error condition.

    Three signals, checked in order:
      1. Site-specific failure markers (``fail_flags`` substring match).
      2. Generic provider / bot-protection wording (``errors.detect``).
      3. HTTP status — 403 (unless suppressed), >=500 server. HTTP 999
         (LinkedIn anti-bot) is a valid "not-found", not an error.
    """
    if fail_flags and html_text:
        for flag, msg in fail_flags.items():
            if flag in html_text:
                return CheckError("Site-specific", msg)

    err = errors.detect(html_text)
    if err:
        return err

    if status_code == 403 and not ignore_403:
        return CheckError("Access denied", f"403 status code, {errors.PROXY_RECOMMENDATION}")
    if status_code == 999:
        return None
    if status_code >= 500:
        return CheckError("Server", f"{status_code} status code")
    return None
