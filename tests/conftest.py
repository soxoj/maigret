from _pytest.mark import Mark


empty_mark = Mark('', [], {})


def by_slow_marker(item):
    return item.get_closest_marker('slow', default=empty_mark)


def pytest_collection_modifyitems(items):
    items.sort(key=by_slow_marker, reverse=False)