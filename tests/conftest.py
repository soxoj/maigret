import glob
import logging
import os

import pytest
from _pytest.mark import Mark

from maigret.sites import MaigretDatabase
from maigret.maigret import setup_arguments_parser
from maigret.settings import Settings
from aiohttp import web


LOCAL_SERVER_PORT = 8080

CUR_PATH = os.path.dirname(os.path.realpath(__file__))
JSON_FILE = os.path.join(CUR_PATH, '../maigret/resources/data.json')
SETTINGS_FILE = os.path.join(CUR_PATH, '../maigret/resources/settings.json')
TEST_JSON_FILE = os.path.join(CUR_PATH, 'db.json')
LOCAL_TEST_JSON_FILE = os.path.join(CUR_PATH, 'local.json')
empty_mark = Mark('', (), {})


RESULTS_EXAMPLE = {
    'Reddit': {
        'cookies': None,
        'parsing_enabled': False,
        'url_main': 'https://www.reddit.com/',
        'username': 'Skyeng',
    },
    'GooglePlayStore': {
        'cookies': None,
        'http_status': 200,
        'is_similar': False,
        'parsing_enabled': False,
        'rank': 1,
        'url_main': 'https://play.google.com/store',
        'url_user': 'https://play.google.com/store/apps/developer?id=Skyeng',
        'username': 'Skyeng',
    },
}


def by_slow_marker(item):
    return item.get_closest_marker('slow', default=empty_mark).name


def pytest_collection_modifyitems(items):
    items.sort(key=by_slow_marker, reverse=False)


def get_test_reports_filenames():
    return glob.glob(os.path.join('report_*'), recursive=False)


def remove_test_reports():
    reports_list = get_test_reports_filenames()
    for f in reports_list:
        os.remove(f)
    logging.error(f'Removed test reports {reports_list}')


@pytest.fixture(scope='session')
def default_db():
    return MaigretDatabase().load_from_file(JSON_FILE)


@pytest.fixture(scope='function')
def test_db():
    return MaigretDatabase().load_from_file(TEST_JSON_FILE)


@pytest.fixture(scope='function')
def local_test_db():
    return MaigretDatabase().load_from_file(LOCAL_TEST_JSON_FILE)


@pytest.fixture(autouse=True)
def reports_autoclean():
    remove_test_reports()
    yield
    remove_test_reports()


@pytest.fixture(scope='session')
def settings():
    settings = Settings()
    settings.load([SETTINGS_FILE])
    return settings


@pytest.fixture(scope='session')
def argparser():
    settings = Settings()
    settings.load([SETTINGS_FILE])
    return setup_arguments_parser(settings)


@pytest.fixture(scope="session")
def httpserver_listen_address():
    return ("localhost", 8989)


@pytest.fixture
async def cookie_test_server():
    async def handle_cookies(request):
        print(f"Received cookies: {request.cookies}")
        cookies_dict = {k: v for k, v in request.cookies.items()}
        return web.json_response({'cookies': cookies_dict})

    app = web.Application()
    app.router.add_get('/cookies', handle_cookies)
    runner = web.AppRunner(app)
    await runner.setup()
    server = web.TCPSite(runner, port=LOCAL_SERVER_PORT)
    await server.start()
    yield server
    await runner.cleanup()
