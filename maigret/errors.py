from typing import Dict, List, Any

from .result import QueryResult
from .types import QueryResultWrapper


# error got as a result of completed search query
class CheckError:
    _type = 'Unknown'
    _desc = ''

    def __init__(self, typename, desc=''):
        self._type = typename
        self._desc = desc

    def __str__(self):
        if not self._desc:
            return f'{self._type} error'

        return f'{self._type} error: {self._desc}'

    @property
    def type(self):
        return self._type

    @property
    def desc(self):
        return self._desc


COMMON_ERRORS = {
    '<title>Attention Required! | Cloudflare</title>': CheckError(
        'Captcha', 'Cloudflare'
    ),
    'Please stand by, while we are checking your browser': CheckError(
        'Bot protection', 'Cloudflare'
    ),
    '<span data-translate="checking_browser">Checking your browser before accessing</span>': CheckError(
        'Bot protection', 'Cloudflare'
    ),
    'This website is using a security service to protect itself from online attacks.': CheckError(
        'Access denied', 'Cloudflare'
    ),
    '<title>Доступ ограничен</title>': CheckError('Censorship', 'Rostelecom'),
    'document.getElementById(\'validate_form_submit\').disabled=true': CheckError(
        'Captcha', 'Mail.ru'
    ),
    'Verifying your browser, please wait...<br>DDoS Protection by</font> Blazingfast.io': CheckError(
        'Bot protection', 'Blazingfast'
    ),
    '404</h1><p class="error-card__description">Мы&nbsp;не&nbsp;нашли страницу': CheckError(
        'Resolving', 'MegaFon 404 page'
    ),
    'Доступ к информационному ресурсу ограничен на основании Федерального закона': CheckError(
        'Censorship', 'MGTS'
    ),
    'Incapsula incident ID': CheckError('Bot protection', 'Incapsula'),
    'Сайт заблокирован хостинг-провайдером': CheckError(
        'Site-specific', 'Site is disabled (Beget)'
    ),
}

ERRORS_TYPES = {
    'Captcha': 'Try to switch to another IP address or to use service cookies',
    'Bot protection': 'Try to switch to another IP address',
    'Censorship': 'switch to another internet service provider',
    'Request timeout': 'Try to increase timeout or to switch to another internet service provider',
}

# TODO: checking for reason
ERRORS_REASONS = {
    'Login required': 'Add authorization cookies through `--cookies-jar-file` (see cookies.txt)',
}

TEMPORARY_ERRORS_TYPES = [
    'Request timeout',
    'Unknown',
    'Request failed',
    'Connecting failure',
    'HTTP',
    'Proxy',
    'Interrupted',
    'Connection lost',
]

THRESHOLD = 3  # percent


def is_important(err_data):
    return err_data['perc'] >= THRESHOLD


def is_permanent(err_type):
    return err_type not in TEMPORARY_ERRORS_TYPES


def detect(text):
    for flag, err in COMMON_ERRORS.items():
        if flag in text:
            return err
    return None


def solution_of(err_type) -> str:
    return ERRORS_TYPES.get(err_type, '')


def extract_and_group(search_res: QueryResultWrapper) -> List[Dict[str, Any]]:
    errors_counts: Dict[str, int] = {}
    for r in search_res.values():
        if r and isinstance(r, dict) and r.get('status'):
            if not isinstance(r['status'], QueryResult):
                continue

            err = r['status'].error
            if not err:
                continue
            errors_counts[err.type] = errors_counts.get(err.type, 0) + 1

    counts = []
    for err, count in sorted(errors_counts.items(), key=lambda x: x[1], reverse=True):
        counts.append(
            {
                'err': err,
                'count': count,
                'perc': round(count / len(search_res), 2) * 100,
            }
        )

    return counts
