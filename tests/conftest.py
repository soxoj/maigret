from _pytest.mark import Mark
from mock import Mock
import os
import pytest

from maigret.sites import MaigretDatabase, MaigretSite

JSON_FILE = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../maigret/resources/data.json')
empty_mark = Mark('', [], {})


def by_slow_marker(item):
    return item.get_closest_marker('slow', default=empty_mark)


def pytest_collection_modifyitems(items):
    items.sort(key=by_slow_marker, reverse=False)


@pytest.fixture(scope='session')
def default_db():
    db = MaigretDatabase().load_from_file(JSON_FILE)

    return db
