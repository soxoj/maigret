import pytest
from maigret.errors import notify_about_errors, CheckError
from maigret.types import QueryResultWrapper
from maigret.result import MaigretCheckResult, MaigretCheckStatus


def test_notify_about_errors():
    results = {
        'site1': {
            'status': MaigretCheckResult(
                '', '', '', MaigretCheckStatus.UNKNOWN, error=CheckError('Captcha')
            )
        },
        'site2': {
            'status': MaigretCheckResult(
                '',
                '',
                '',
                MaigretCheckStatus.UNKNOWN,
                error=CheckError('Bot protection'),
            )
        },
        'site3': {
            'status': MaigretCheckResult(
                '',
                '',
                '',
                MaigretCheckStatus.UNKNOWN,
                error=CheckError('Access denied'),
            )
        },
        'site4': {
            'status': MaigretCheckResult(
                '', '', '', MaigretCheckStatus.CLAIMED, error=None
            )
        },
    }

    results = notify_about_errors(results, query_notify=None, show_statistics=True)

    # Check the output
    expected_output = [
        (
            'Too many errors of type "Captcha" (25.0%). Try to switch to another ip address or to use service cookies',
            '!',
        ),
        (
            'Too many errors of type "Bot protection" (25.0%). Try to switch to another ip address',
            '!',
        ),
        ('Too many errors of type "Access denied" (25.0%)', '!'),
        ('Verbose error statistics:', '-'),
        ('Captcha: 25.0%', '!'),
        ('Bot protection: 25.0%', '!'),
        ('Access denied: 25.0%', '!'),
        ('You can see detailed site check errors with a flag `--print-errors`', '-'),
    ]
    assert results == expected_output
