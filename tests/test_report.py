"""Maigret reports test functions"""
import copy
import json
import os
from io import StringIO

import xmind
from jinja2 import Template

from maigret.report import generate_csv_report, generate_txt_report, save_xmind_report, save_html_report, \
    save_pdf_report, generate_report_template, generate_report_context, generate_json_report
from maigret.result import QueryResult, QueryStatus

EXAMPLE_RESULTS = {
    'GitHub': {
        'username': 'test',
        'parsing_enabled': True,
        'url_main': 'https://www.github.com/',
        'url_user': 'https://www.github.com/test',
        'status': QueryResult('test',
                              'GitHub',
                              'https://www.github.com/test',
                              QueryStatus.CLAIMED,
                              tags=['test_tag']),
        'http_status': 200,
        'is_similar': False,
        'rank': 78
    }
}

GOOD_RESULT = QueryResult('', '', '', QueryStatus.CLAIMED)
BAD_RESULT = QueryResult('', '', '', QueryStatus.AVAILABLE)

GOOD_500PX_RESULT = copy.deepcopy(GOOD_RESULT)
GOOD_500PX_RESULT.tags = ['photo', 'us', 'global']
GOOD_500PX_RESULT.ids_data = {"uid": "dXJpOm5vZGU6VXNlcjoyNjQwMzQxNQ==", "legacy_id": "26403415",
                              "username": "alexaimephotographycars", "name": "Alex Aim\u00e9",
                              "website": "www.flickr.com/photos/alexaimephotography/",
                              "facebook_link": " www.instagram.com/street.reality.photography/",
                              "instagram_username": "alexaimephotography", "twitter_username": "Alexaimephotogr"}

GOOD_REDDIT_RESULT = copy.deepcopy(GOOD_RESULT)
GOOD_REDDIT_RESULT.tags = ['news', 'us']
GOOD_REDDIT_RESULT.ids_data = {"reddit_id": "t5_1nytpy", "reddit_username": "alexaimephotography",
                               "fullname": "alexaimephotography",
                               "image": "https://styles.redditmedia.com/t5_1nytpy/styles/profileIcon_7vmhdwzd3g931.jpg?width=256&height=256&crop=256:256,smart&frame=1&s=4f355f16b4920844a3f4eacd4237a7bf76b2e97e",
                               "is_employee": "False", "is_nsfw": "False", "is_mod": "True", "is_following": "True",
                               "has_user_profile": "True", "hide_from_robots": "False",
                               "created_at": "2019-07-10 12:20:03", "total_karma": "53959", "post_karma": "52738"}

GOOD_IG_RESULT = copy.deepcopy(GOOD_RESULT)
GOOD_IG_RESULT.tags = ['photo', 'global']
GOOD_IG_RESULT.ids_data = {"instagram_username": "alexaimephotography", "fullname": "Alexaimephotography",
                           "id": "6828488620",
                           "image": "https://scontent-hel3-1.cdninstagram.com/v/t51.2885-19/s320x320/95420076_1169632876707608_8741505804647006208_n.jpg?_nc_ht=scontent-hel3-1.cdninstagram.com&_nc_ohc=jd87OUGsX4MAX_Ym5GX&tp=1&oh=0f42badd68307ba97ec7fb1ef7b4bfd4&oe=601E5E6F",
                           "bio": "Photographer \nChild of fine street arts",
                           "external_url": "https://www.flickr.com/photos/alexaimephotography2020/"}

GOOD_TWITTER_RESULT = copy.deepcopy(GOOD_RESULT)
GOOD_TWITTER_RESULT.tags = ['social', 'us']

TEST = [('alexaimephotographycars', 'username', {
    '500px': {'username': 'alexaimephotographycars', 'parsing_enabled': True, 'url_main': 'https://500px.com/',
              'url_user': 'https://500px.com/p/alexaimephotographycars',
              'ids_usernames': {'alexaimephotographycars': 'username', 'alexaimephotography': 'username',
                                'Alexaimephotogr': 'username'}, 'status': GOOD_500PX_RESULT, 'http_status': 200,
              'is_similar': False, 'rank': 2981},
    'Reddit': {'username': 'alexaimephotographycars', 'parsing_enabled': True, 'url_main': 'https://www.reddit.com/',
               'url_user': 'https://www.reddit.com/user/alexaimephotographycars', 'status': BAD_RESULT,
               'http_status': 404, 'is_similar': False, 'rank': 17},
    'Twitter': {'username': 'alexaimephotographycars', 'parsing_enabled': True, 'url_main': 'https://www.twitter.com/',
                'url_user': 'https://twitter.com/alexaimephotographycars', 'status': BAD_RESULT, 'http_status': 400,
                'is_similar': False, 'rank': 55},
    'Instagram': {'username': 'alexaimephotographycars', 'parsing_enabled': True,
                  'url_main': 'https://www.instagram.com/',
                  'url_user': 'https://www.instagram.com/alexaimephotographycars', 'status': BAD_RESULT,
                  'http_status': 404, 'is_similar': False, 'rank': 29}}), ('alexaimephotography', 'username', {
    '500px': {'username': 'alexaimephotography', 'parsing_enabled': True, 'url_main': 'https://500px.com/',
              'url_user': 'https://500px.com/p/alexaimephotography', 'status': BAD_RESULT, 'http_status': 200,
              'is_similar': False, 'rank': 2981},
    'Reddit': {'username': 'alexaimephotography', 'parsing_enabled': True, 'url_main': 'https://www.reddit.com/',
               'url_user': 'https://www.reddit.com/user/alexaimephotography',
               'ids_usernames': {'alexaimephotography': 'username'}, 'status': GOOD_REDDIT_RESULT, 'http_status': 200,
               'is_similar': False, 'rank': 17},
    'Twitter': {'username': 'alexaimephotography', 'parsing_enabled': True, 'url_main': 'https://www.twitter.com/',
                'url_user': 'https://twitter.com/alexaimephotography', 'status': BAD_RESULT, 'http_status': 400,
                'is_similar': False, 'rank': 55},
    'Instagram': {'username': 'alexaimephotography', 'parsing_enabled': True, 'url_main': 'https://www.instagram.com/',
                  'url_user': 'https://www.instagram.com/alexaimephotography',
                  'ids_usernames': {'alexaimephotography': 'username'}, 'status': GOOD_IG_RESULT, 'http_status': 200,
                  'is_similar': False, 'rank': 29}}), ('Alexaimephotogr', 'username', {
    '500px': {'username': 'Alexaimephotogr', 'parsing_enabled': True, 'url_main': 'https://500px.com/',
              'url_user': 'https://500px.com/p/Alexaimephotogr', 'status': BAD_RESULT, 'http_status': 200,
              'is_similar': False, 'rank': 2981},
    'Reddit': {'username': 'Alexaimephotogr', 'parsing_enabled': True, 'url_main': 'https://www.reddit.com/',
               'url_user': 'https://www.reddit.com/user/Alexaimephotogr', 'status': BAD_RESULT, 'http_status': 404,
               'is_similar': False, 'rank': 17},
    'Twitter': {'username': 'Alexaimephotogr', 'parsing_enabled': True, 'url_main': 'https://www.twitter.com/',
                'url_user': 'https://twitter.com/Alexaimephotogr', 'status': GOOD_TWITTER_RESULT, 'http_status': 400,
                'is_similar': False, 'rank': 55},
    'Instagram': {'username': 'Alexaimephotogr', 'parsing_enabled': True, 'url_main': 'https://www.instagram.com/',
                  'url_user': 'https://www.instagram.com/Alexaimephotogr', 'status': BAD_RESULT, 'http_status': 404,
                  'is_similar': False, 'rank': 29}})]

SUPPOSED_BRIEF = """Search by username alexaimephotographycars returned 1 accounts. Found target's other IDs: alexaimephotography, Alexaimephotogr. Search by username alexaimephotography returned 2 accounts. Search by username Alexaimephotogr returned 1 accounts. Extended info extracted from 3 accounts."""

SUPPOSED_INTERESTS = "Interests: photo <span class=\"text-muted\">(2)</span>, news <span class=\"text-muted\">(1)</span>, social <span class=\"text-muted\">(1)</span>"

SUPPOSED_GEO = "Geo: us <span class=\"text-muted\">(3)</span>"


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


def test_generate_txt_report():
    txtfile = StringIO()
    generate_txt_report('test', EXAMPLE_RESULTS, txtfile)

    txtfile.seek(0)
    data = txtfile.readlines()

    assert data == [
        'https://www.github.com/test\n',
        'Total Websites Username Detected On : 1',
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
    assert data['topic']['topics'][1]['topics'][0]['label'] == 'https://www.github.com/test'


def test_html_report():
    report_name = 'report_test.html'
    context = generate_report_context(TEST)
    save_html_report(report_name, context)

    report_text = open(report_name).read()

    assert SUPPOSED_BRIEF in report_text
    assert SUPPOSED_GEO in report_text
    assert SUPPOSED_INTERESTS in report_text


def test_pdf_report():
    report_name = 'report_test.pdf'
    context = generate_report_context(TEST)
    save_pdf_report(report_name, context)

    assert os.path.exists(report_name)
