from maigret.error_detection import ErrorPageDetector
from maigret.errors import CheckError

def test_site_specific_error():
    detector = ErrorPageDetector(
        {"blocked": "Blocked by site"},
        ignore_403=False,
    )

    err = detector.detect("this page is blocked", 200)

    assert isinstance(err, CheckError)
    assert err.type == "Site-specific"


def test_http_403():
    detector = ErrorPageDetector({}, ignore_403=False)

    err = detector.detect("x", 403)

    assert err.type == "Access denied"

def test_http_500():
    detector = ErrorPageDetector({}, ignore_403=False)

    err = detector.detect("x", 500)

    assert err.type == "Server"

def test_no_error():
    detector = ErrorPageDetector({}, ignore_403=False)

    assert detector.detect("ok", 200) is None