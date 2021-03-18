import glob
import logging
import os

import pytest
from _pytest.mark import Mark

from maigret.sites import MaigretDatabase

CUR_PATH = os.path.dirname(os.path.realpath(__file__))
JSON_FILE = os.path.join(CUR_PATH, '../maigret/resources/data.json')
empty_mark = Mark('', [], {})


def by_slow_marker(item):
    return item.get_closest_marker('slow', default=empty_mark)


def pytest_collection_modifyitems(items):
    items.sort(key=by_slow_marker, reverse=False)


def get_test_reports_filenames():
    return glob.glob(os.path.join('report_*'), recursive=False)


def remove_test_reports():
    reports_list = get_test_reports_filenames()
    for f in reports_list: os.remove(f)
    logging.error(f'Removed test reports {reports_list}')


@pytest.fixture(scope='session')
def default_db():
    db = MaigretDatabase().load_from_file(JSON_FILE)

    return db


@pytest.fixture(autouse=True)
def reports_autoclean():
    remove_test_reports()
    yield
    remove_test_reports()
