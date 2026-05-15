"""Maigret reports test functions"""

import copy
import json
import os
import subprocess
import sys
import textwrap
import pytest
from io import StringIO

import xmind  # type: ignore[import-untyped]
from jinja2 import Template

from maigret.report import (
    filter_supposed_data,
    sort_report_by_data_points,
    _md_format_value,
    generate_csv_report,
    generate_txt_report,
    save_csv_report,
    save_txt_report,
    save_json_report,
    save_markdown_report,
    save_xmind_report,
    save_html_report,
    save_pdf_report,
    generate_report_template,
    generate_report_context,
    generate_json_report,
    get_plaintext_report,
)
from maigret.result import MaigretCheckResult, MaigretCheckStatus
from maigret.sites import MaigretSite


GOOD_RESULT = MaigretCheckResult('', '', '', MaigretCheckStatus.CLAIMED)
BAD_RESULT = MaigretCheckResult('', '', '', MaigretCheckStatus.AVAILABLE)

EXAMPLE_RESULTS = {
    'GitHub': {
        'username': 'test',
        'parsing_enabled': True,
        'url_main': 'https://www.github.com/',
        'url_user': 'https://www.github.com/test',
        'status': MaigretCheckResult(
            'test',
            'GitHub',
            'https://www.github.com/test',
            MaigretCheckStatus.CLAIMED,
            tags=['test_tag'],
        ),
        'http_status': 200,
        'is_similar': False,
        'rank': 78,
        'site': MaigretSite('test', {}),
    }
}

BROKEN_RESULTS = {
    'GitHub': {
        'username': 'test',
        'parsing_enabled': True,
        'url_main': 'https://www.github.com/',
        'url_user': 'https://www.github.com/test',
        'http_status': 200,
        'is_similar': False,
        'rank': 78,
        'site': MaigretSite('test', {}),
    }
}

GOOD_500PX_RESULT = copy.deepcopy(GOOD_RESULT)
GOOD_500PX_RESULT.tags = ['photo', 'us', 'global']
GOOD_500PX_RESULT.ids_data = {
    "uid": "dXJpOm5vZGU6VXNlcjoyNjQwMzQxNQ==",
    "legacy_id": "26403415",
    "username": "alexaimephotographycars",
    "name": "Alex Aim\u00e9",
    "website": "www.flickr.com/photos/alexaimephotography/",
    "facebook_link": " www.instagram.com/street.reality.photography/",
    "instagram_username": "alexaimephotography",
    "twitter_username": "Alexaimephotogr",
}

GOOD_REDDIT_RESULT = copy.deepcopy(GOOD_RESULT)
GOOD_REDDIT_RESULT.tags = ['news', 'us']
GOOD_REDDIT_RESULT.ids_data = {
    "reddit_id": "t5_1nytpy",
    "reddit_username": "alexaimephotography",
    "fullname": "alexaimephotography",
    "image": "https://styles.redditmedia.com/t5_1nytpy/styles/profileIcon_7vmhdwzd3g931.jpg?width=256&height=256&crop=256:256,smart&frame=1&s=4f355f16b4920844a3f4eacd4237a7bf76b2e97e",
    "is_employee": "False",
    "is_nsfw": "False",
    "is_mod": "True",
    "is_following": "True",
    "has_user_profile": "True",
    "hide_from_robots": "False",
    "created_at": "2019-07-10 12:20:03",
    "total_karma": "53959",
    "post_karma": "52738",
}

GOOD_IG_RESULT = copy.deepcopy(GOOD_RESULT)
GOOD_IG_RESULT.tags = ['photo', 'global']
GOOD_IG_RESULT.ids_data = {
    "instagram_username": "alexaimephotography",
    "fullname": "Alexaimephotography",
    "id": "6828488620",
    "image": "https://scontent-hel3-1.cdninstagram.com/v/t51.2885-19/s320x320/95420076_1169632876707608_8741505804647006208_n.jpg?_nc_ht=scontent-hel3-1.cdninstagram.com&_nc_ohc=jd87OUGsX4MAX_Ym5GX&tp=1&oh=0f42badd68307ba97ec7fb1ef7b4bfd4&oe=601E5E6F",
    "bio": "Photographer \nChild of fine street arts",
    "external_url": "https://www.flickr.com/photos/alexaimephotography2020/",
}

GOOD_TWITTER_RESULT = copy.deepcopy(GOOD_RESULT)
GOOD_TWITTER_RESULT.tags = ['social', 'us']

TEST = [
    (
        'alexaimephotographycars',
        'username',
        {
            '500px': {
                'username': 'alexaimephotographycars',
                'parsing_enabled': True,
                'url_main': 'https://500px.com/',
                'url_user': 'https://500px.com/p/alexaimephotographycars',
                'ids_usernames': {
                    'alexaimephotographycars': 'username',
                    'alexaimephotography': 'username',
                    'Alexaimephotogr': 'username',
                },
                'status': GOOD_500PX_RESULT,
                'http_status': 200,
                'is_similar': False,
                'rank': 2981,
            },
            'Reddit': {
                'username': 'alexaimephotographycars',
                'parsing_enabled': True,
                'url_main': 'https://www.reddit.com/',
                'url_user': 'https://www.reddit.com/user/alexaimephotographycars',
                'status': BAD_RESULT,
                'http_status': 404,
                'is_similar': False,
                'rank': 17,
            },
            'Twitter': {
                'username': 'alexaimephotographycars',
                'parsing_enabled': True,
                'url_main': 'https://www.twitter.com/',
                'url_user': 'https://twitter.com/alexaimephotographycars',
                'status': BAD_RESULT,
                'http_status': 400,
                'is_similar': False,
                'rank': 55,
            },
            'Instagram': {
                'username': 'alexaimephotographycars',
                'parsing_enabled': True,
                'url_main': 'https://www.instagram.com/',
                'url_user': 'https://www.instagram.com/alexaimephotographycars',
                'status': BAD_RESULT,
                'http_status': 404,
                'is_similar': False,
                'rank': 29,
            },
        },
    ),
    (
        'alexaimephotography',
        'username',
        {
            '500px': {
                'username': 'alexaimephotography',
                'parsing_enabled': True,
                'url_main': 'https://500px.com/',
                'url_user': 'https://500px.com/p/alexaimephotography',
                'status': BAD_RESULT,
                'http_status': 200,
                'is_similar': False,
                'rank': 2981,
            },
            'Reddit': {
                'username': 'alexaimephotography',
                'parsing_enabled': True,
                'url_main': 'https://www.reddit.com/',
                'url_user': 'https://www.reddit.com/user/alexaimephotography',
                'ids_usernames': {'alexaimephotography': 'username'},
                'status': GOOD_REDDIT_RESULT,
                'http_status': 200,
                'is_similar': False,
                'rank': 17,
            },
            'Twitter': {
                'username': 'alexaimephotography',
                'parsing_enabled': True,
                'url_main': 'https://www.twitter.com/',
                'url_user': 'https://twitter.com/alexaimephotography',
                'status': BAD_RESULT,
                'http_status': 400,
                'is_similar': False,
                'rank': 55,
            },
            'Instagram': {
                'username': 'alexaimephotography',
                'parsing_enabled': True,
                'url_main': 'https://www.instagram.com/',
                'url_user': 'https://www.instagram.com/alexaimephotography',
                'ids_usernames': {'alexaimephotography': 'username'},
                'status': GOOD_IG_RESULT,
                'http_status': 200,
                'is_similar': False,
                'rank': 29,
            },
        },
    ),
    (
        'Alexaimephotogr',
        'username',
        {
            '500px': {
                'username': 'Alexaimephotogr',
                'parsing_enabled': True,
                'url_main': 'https://500px.com/',
                'url_user': 'https://500px.com/p/Alexaimephotogr',
                'status': BAD_RESULT,
                'http_status': 200,
                'is_similar': False,
                'rank': 2981,
            },
            'Reddit': {
                'username': 'Alexaimephotogr',
                'parsing_enabled': True,
                'url_main': 'https://www.reddit.com/',
                'url_user': 'https://www.reddit.com/user/Alexaimephotogr',
                'status': BAD_RESULT,
                'http_status': 404,
                'is_similar': False,
                'rank': 17,
            },
            'Twitter': {
                'username': 'Alexaimephotogr',
                'parsing_enabled': True,
                'url_main': 'https://www.twitter.com/',
                'url_user': 'https://twitter.com/Alexaimephotogr',
                'status': GOOD_TWITTER_RESULT,
                'http_status': 400,
                'is_similar': False,
                'rank': 55,
            },
            'Instagram': {
                'username': 'Alexaimephotogr',
                'parsing_enabled': True,
                'url_main': 'https://www.instagram.com/',
                'url_user': 'https://www.instagram.com/Alexaimephotogr',
                'status': BAD_RESULT,
                'http_status': 404,
                'is_similar': False,
                'rank': 29,
            },
        },
    ),
]

SUPPOSED_BRIEF = """Search by username alexaimephotographycars returned 1 accounts. Found target's other IDs: alexaimephotography, Alexaimephotogr. Search by username alexaimephotography returned 2 accounts. Search by username Alexaimephotogr returned 1 accounts. Extended info extracted from 3 accounts."""
SUPPOSED_BROKEN_BRIEF = """Search by username alexaimephotographycars returned 0 accounts. Search by username alexaimephotography returned 2 accounts. Search by username Alexaimephotogr returned 1 accounts. Extended info extracted from 2 accounts."""

SUPPOSED_GEO = "Geo: us <span class=\"text-muted\">(3)</span>"
SUPPOSED_BROKEN_GEO = "Geo: us <span class=\"text-muted\">(2)</span>"

SUPPOSED_INTERESTS = "Interests: photo <span class=\"text-muted\">(2)</span>, news <span class=\"text-muted\">(1)</span>, social <span class=\"text-muted\">(1)</span>"
SUPPOSED_BROKEN_INTERESTS = "Interests: news <span class=\"text-muted\">(1)</span>, photo <span class=\"text-muted\">(1)</span>, social <span class=\"text-muted\">(1)</span>"


def test_generate_report_template():
    report_template, css = generate_report_template(is_pdf=True)

    assert isinstance(report_template, Template)
    assert isinstance(css, str)

    report_template, css = generate_report_template(is_pdf=False)

    assert isinstance(report_template, Template)
    assert css is None


def test_generate_csv_report():
    csvfile = StringIO()
    generate_csv_report('test', EXAMPLE_RESULTS, csvfile)

    csvfile.seek(0)
    data = csvfile.readlines()

    assert data == [
        'username,name,url_main,url_user,exists,http_status\r\n',
        'test,GitHub,https://www.github.com/,https://www.github.com/test,Claimed,200\r\n',
    ]


def test_generate_csv_report_broken():
    csvfile = StringIO()
    generate_csv_report('test', BROKEN_RESULTS, csvfile)

    csvfile.seek(0)
    data = csvfile.readlines()

    assert data == [
        'username,name,url_main,url_user,exists,http_status\r\n',
        'test,GitHub,https://www.github.com/,https://www.github.com/test,Unknown,200\r\n',
    ]


def test_generate_txt_report():
    txtfile = StringIO()
    generate_txt_report('test', EXAMPLE_RESULTS, txtfile)

    txtfile.seek(0)
    data = txtfile.readlines()

    assert data == [
        'https://www.github.com/test\n',
        'Total Websites Username Detected On : 1',
    ]


def test_generate_txt_report_broken():
    txtfile = StringIO()
    generate_txt_report('test', BROKEN_RESULTS, txtfile)

    txtfile.seek(0)
    data = txtfile.readlines()

    assert data == [
        'Total Websites Username Detected On : 0',
    ]


def test_generate_json_simple_report():
    jsonfile = StringIO()
    MODIFIED_RESULTS = dict(EXAMPLE_RESULTS)
    MODIFIED_RESULTS['GitHub2'] = EXAMPLE_RESULTS['GitHub']
    generate_json_report('test', MODIFIED_RESULTS, jsonfile, 'simple')

    jsonfile.seek(0)
    data = jsonfile.readlines()

    assert len(data) == 1
    assert list(json.loads(data[0]).keys()) == ['GitHub', 'GitHub2']


def test_generate_json_simple_report_broken():
    jsonfile = StringIO()
    MODIFIED_RESULTS = dict(BROKEN_RESULTS)
    MODIFIED_RESULTS['GitHub2'] = BROKEN_RESULTS['GitHub']
    generate_json_report('test', BROKEN_RESULTS, jsonfile, 'simple')

    jsonfile.seek(0)
    data = jsonfile.readlines()

    assert len(data) == 1
    assert list(json.loads(data[0]).keys()) == []


def test_generate_json_ndjson_report():
    jsonfile = StringIO()
    MODIFIED_RESULTS = dict(EXAMPLE_RESULTS)
    MODIFIED_RESULTS['GitHub2'] = EXAMPLE_RESULTS['GitHub']
    generate_json_report('test', MODIFIED_RESULTS, jsonfile, 'ndjson')

    jsonfile.seek(0)
    data = jsonfile.readlines()

    assert len(data) == 2
    assert json.loads(data[0])['sitename'] == 'GitHub'


def test_save_xmind_report():
    filename = 'report_test.xmind'
    save_xmind_report(filename, 'test', EXAMPLE_RESULTS)

    workbook = xmind.load(filename)
    sheet = workbook.getPrimarySheet()
    data = sheet.getData()

    assert data['title'] == 'test Analysis'
    assert data['topic']['title'] == 'test'
    assert len(data['topic']['topics']) == 2
    assert data['topic']['topics'][0]['title'] == 'Undefined'
    assert data['topic']['topics'][1]['title'] == 'test_tag'
    assert len(data['topic']['topics'][1]['topics']) == 1
    assert (
        data['topic']['topics'][1]['topics'][0]['label']
        == 'https://www.github.com/test'
    )


def test_save_xmind_report_broken():
    filename = 'report_test.xmind'
    save_xmind_report(filename, 'test', BROKEN_RESULTS)

    workbook = xmind.load(filename)
    sheet = workbook.getPrimarySheet()
    data = sheet.getData()

    assert data['title'] == 'test Analysis'
    assert data['topic']['title'] == 'test'
    assert len(data['topic']['topics']) == 1
    assert data['topic']['topics'][0]['title'] == 'Undefined'


def test_html_report():
    report_name = 'report_test.html'
    context = generate_report_context(TEST)
    save_html_report(report_name, context)

    report_text = open(report_name).read()

    assert SUPPOSED_BRIEF in report_text
    assert SUPPOSED_GEO in report_text
    assert SUPPOSED_INTERESTS in report_text


def test_html_report_broken():
    report_name = 'report_test_broken.html'
    BROKEN_DATA = copy.deepcopy(TEST)
    BROKEN_DATA[0][2]['500px']['status'] = None

    context = generate_report_context(BROKEN_DATA)
    save_html_report(report_name, context)

    report_text = open(report_name).read()

    assert SUPPOSED_BROKEN_BRIEF in report_text
    assert SUPPOSED_BROKEN_GEO in report_text
    assert SUPPOSED_BROKEN_INTERESTS in report_text


@pytest.mark.skip(reason='connection reset, fixme')
def test_pdf_report():
    report_name = 'report_test.pdf'
    context = generate_report_context(TEST)
    save_pdf_report(report_name, context)

    assert os.path.exists(report_name)


def test_save_pdf_report_raises_helpful_error_without_xhtml2pdf(
    monkeypatch, tmp_path
):
    # Setting an entry to None makes a subsequent `import` raise ImportError —
    # this simulates the optional 'pdf' extra not being installed without
    # actually uninstalling xhtml2pdf from the test environment.
    monkeypatch.setitem(sys.modules, 'xhtml2pdf', None)
    monkeypatch.setitem(sys.modules, 'xhtml2pdf.pisa', None)

    context = generate_report_context(TEST)
    target = tmp_path / "report.pdf"

    with pytest.raises(RuntimeError) as excinfo:
        save_pdf_report(str(target), context)

    msg = str(excinfo.value)
    assert "maigret[pdf]" in msg
    assert "pip install" in msg
    assert not target.exists()


def test_xhtml2pdf_is_not_module_level_dependency():
    # Guard against a regression where someone hoists `import xhtml2pdf` /
    # `from xhtml2pdf import pisa` to the top of maigret/report.py — that
    # would force every Maigret user to install the optional extra.
    import maigret.report as report_module

    module_globals = vars(report_module)
    assert 'xhtml2pdf' not in module_globals
    assert 'pisa' not in module_globals


def test_import_maigret_without_pdf_extras():
    # End-to-end check: spawn a fresh interpreter with every package in the
    # [pdf] extra blocked before any maigret module is loaded, and confirm
    # the package, the report module, and save_pdf_report itself all import
    # cleanly. Mirrors what a user who ran `pip install maigret` (without
    # [pdf]) would experience.
    code = textwrap.dedent(
        """
        import sys
        for name in (
            'xhtml2pdf', 'xhtml2pdf.pisa',
            'arabic_reshaper',
            'bidi', 'bidi.algorithm',
        ):
            sys.modules[name] = None

        import maigret
        import maigret.report
        from maigret.report import save_pdf_report

        assert callable(save_pdf_report)
        print("OK")
        """
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    assert "OK" in result.stdout


def test_text_report():
    context = generate_report_context(TEST)
    report_text = get_plaintext_report(context)

    for brief_part in SUPPOSED_BRIEF.split():
        assert brief_part in report_text
    assert 'us' in report_text
    assert 'photo' in report_text


def test_text_report_broken():
    BROKEN_DATA = copy.deepcopy(TEST)
    BROKEN_DATA[0][2]['500px']['status'] = None

    context = generate_report_context(BROKEN_DATA)
    report_text = get_plaintext_report(context)

    for brief_part in SUPPOSED_BROKEN_BRIEF.split():
        assert brief_part in report_text
    assert 'us' in report_text
    assert 'photo' in report_text


def test_filter_supposed_data():
    data = {
        'fullname': ['Alice'],
        'gender': ['female'],
        'location': ['Berlin'],
        'age': ['30'],
        'email': ['x@y.z'],  # not allowed, must be dropped
        'bio': ['hi'],  # not allowed
    }
    result = filter_supposed_data(data)
    assert result == {
        'Fullname': 'Alice',
        'Gender': 'female',
        'Location': 'Berlin',
        'Age': '30',
    }


def test_filter_supposed_data_empty():
    assert filter_supposed_data({}) == {}
    assert filter_supposed_data({'nope': ['v']}) == {}


def test_filter_supposed_data_scalar_values():
    # Strings and scalars must be kept whole — previously v[0] on "Alice"
    # silently returned "A" instead of "Alice".
    data = {
        'fullname': 'Alice',
        'gender': 'female',
        'location': 'Berlin',
        'age': 30,
    }
    assert filter_supposed_data(data) == {
        'Fullname': 'Alice',
        'Gender': 'female',
        'Location': 'Berlin',
        'Age': 30,
    }


def test_filter_supposed_data_empty_list_yields_empty_string():
    # Edge case: list value present but empty should not crash with IndexError.
    assert filter_supposed_data({'fullname': []}) == {'Fullname': ''}


def test_filter_supposed_data_mixed_values():
    # List and scalar mixed in the same payload.
    data = {'fullname': ['Alice', 'Alicia'], 'gender': 'female'}
    assert filter_supposed_data(data) == {
        'Fullname': 'Alice',
        'Gender': 'female',
    }


def test_sort_report_by_data_points():
    status_many = MaigretCheckResult('', '', '', MaigretCheckStatus.CLAIMED)
    status_many.ids_data = {'a': 1, 'b': 2, 'c': 3}
    status_one = MaigretCheckResult('', '', '', MaigretCheckStatus.CLAIMED)
    status_one.ids_data = {'a': 1}
    status_none = MaigretCheckResult('', '', '', MaigretCheckStatus.CLAIMED)

    results = {
        'few': {'status': status_one},
        'many': {'status': status_many},
        'zero': {'status': status_none},
        'nostatus': {},
    }
    sorted_out = sort_report_by_data_points(results)
    keys = list(sorted_out.keys())
    # site with 3 ids_data fields must come first
    assert keys[0] == 'many'
    # site with 1 field next
    assert keys[1] == 'few'


def test_md_format_value_list():
    assert _md_format_value(['a', 'b', 'c']) == 'a, b, c'


def test_md_format_value_url():
    assert _md_format_value('https://example.com') == '[https://example.com](https://example.com)'
    assert _md_format_value('http://x.y') == '[http://x.y](http://x.y)'


def test_md_format_value_plain():
    assert _md_format_value('hello') == 'hello'
    assert _md_format_value(42) == '42'


def test_save_csv_report():
    filename = 'report_test.csv'
    save_csv_report(filename, 'test', EXAMPLE_RESULTS)
    with open(filename) as f:
        content = f.read()
    assert 'username,name,url_main' in content
    assert 'test,GitHub' in content


def test_save_txt_report():
    filename = 'report_test.txt'
    save_txt_report(filename, 'test', EXAMPLE_RESULTS)
    with open(filename) as f:
        content = f.read()
    assert 'https://www.github.com/test' in content
    assert 'Total Websites Username Detected On : 1' in content


def test_save_json_report_simple():
    filename = 'report_test.json'
    save_json_report(filename, 'test', EXAMPLE_RESULTS, 'simple')
    with open(filename) as f:
        data = json.load(f)
    assert 'GitHub' in data


def test_save_json_report_ndjson():
    filename = 'report_test_ndjson.json'
    save_json_report(filename, 'test', EXAMPLE_RESULTS, 'ndjson')
    with open(filename) as f:
        lines = f.readlines()
    assert len(lines) == 1
    assert json.loads(lines[0])['sitename'] == 'GitHub'


def _markdown_context_with_rich_ids():
    """Build a context with found accounts, ids_data (incl. image, url, list) to exercise all branches."""
    found_result = copy.deepcopy(GOOD_RESULT)
    found_result.tags = ['photo', 'us']
    found_result.ids_data = {
        "fullname": "Alice",
        "name": "Alice A.",
        "location": "Berlin",
        "bio": "Photographer",
        "external_url": "https://example.com/profile",
        "image": "https://example.com/avatar.png",  # must be skipped
        "aliases": ["alice", "alicea"],  # list value
        "last_online": "2024-01-02 10:00:00",
    }
    data = {
        'Github': {
            'username': 'alice',
            'parsing_enabled': True,
            'url_main': 'https://github.com/',
            'url_user': 'https://github.com/alice',
            'status': found_result,
            'http_status': 200,
            'is_similar': False,
            'rank': 1,
            'site': MaigretSite('Github', {}),
            'found': True,
            'ids_data': found_result.ids_data,
        },
        'Similar': {
            'username': 'alice',
            'url_user': 'https://other.com/alice',
            'is_similar': True,
            'found': True,
            'status': copy.deepcopy(GOOD_RESULT),
        },
    }
    return {
        'username': 'alice',
        'generated_at': '2024-01-02 10:00',
        'brief': 'Search returned 1 account',
        'countries_tuple_list': [('us', 1)],
        'interests_tuple_list': [('photo', 1)],
        'first_seen': '2023-01-01',
        'results': [('alice', 'username', data)],
    }


def test_save_markdown_report():
    filename = 'report_test.md'
    context = _markdown_context_with_rich_ids()
    save_markdown_report(filename, context, run_info={'sites_count': 100, 'flags': '--top-sites 100'})
    with open(filename) as f:
        content = f.read()
    assert '# Report by searching on username "alice"' in content
    assert '## Summary' in content
    assert '## Accounts found' in content
    assert '### Github' in content
    assert '[https://github.com/alice](https://github.com/alice)' in content
    assert 'Ethical use' in content
    assert '100 sites checked' in content
    # image field must NOT appear in per-site listing
    assert 'avatar.png' not in content
    # list field rendered with join
    assert 'alice, alicea' in content
    # external url formatted as markdown link
    assert '[https://example.com/profile](https://example.com/profile)' in content


def test_save_markdown_report_minimal_context():
    """No run_info, no first_seen — exercise the fallback branches."""
    filename = 'report_test_min.md'
    context = {
        'username': 'bob',
        'brief': 'nothing found',
        'results': [],
    }
    save_markdown_report(filename, context)
    with open(filename) as f:
        content = f.read()
    assert '# Report by searching on username "bob"' in content
    assert '## Summary' in content


def test_get_plaintext_report_minimal():
    """Minimal context without countries/interests."""
    context = {
        'brief': 'Nothing to report.',
        'interests_tuple_list': [],
        'countries_tuple_list': [],
    }
    out = get_plaintext_report(context)
    assert 'Nothing to report.' in out
    assert 'Countries:' not in out
    assert 'Interests' not in out
