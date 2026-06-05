from typing import Optional

from maigret import errors
from maigret.errors import CheckError


class ErrorPageDetector:
    """
    Detect common error states in webpage responses.

    Handles:
    - site-specific failure markers
    - generic provider/bot-protection errors
    - HTTP status-based failures
    """

    def __init__(self, fail_flags=None, ignore_403=False):
        self.fail_flags = fail_flags
        self.ignore_403 = ignore_403

    def detect(
        self,
        html_text: str,
        status_code: int,
    ) -> Optional[CheckError]:
        """
        Detect an error condition from page content and HTTP status.
        """

        # Site-specific restriction markers
        err = self._detect_site_specific(html_text)
        if err:
            return err

        # Generic censorship / bot-protection detection
        err = self._detect_common(html_text)
        if err:
            return err

        # HTTP status-based detection
        return self._detect_http(status_code)

    def _detect_site_specific(
        self,
        html_text: str,
    ) -> Optional[CheckError]:

        # Detect service restrictions such as a country restriction
        for flag, msg in self.fail_flags.items():
            if html_text and flag in html_text:
                return CheckError("Site-specific", msg)

        return None

    def _detect_common(
        self,
        html_text: str,
    ) -> Optional[CheckError]:

        return errors.detect(html_text)

    def _detect_http(
        self,
        status_code: int,
    ) -> Optional[CheckError]:

        # Detect common site errors
        if status_code == 403 and not self.ignore_403:
            return CheckError("Access denied",
                              f"403 status code, {errors.PROXY_RECOMMENDATION}")

        # LinkedIn anti-bot /
        # HTTP 999 workaround. It shouldn't trigger an infrastructure
        # Server Error because it represents a valid "Not Found /
        # Blocked" state for the username.
        elif status_code == 999:
            return None

        # Server-side failure
        elif status_code >= 500:
            return CheckError(
                "Server",
                f"{status_code} status code",
            )

        return None
