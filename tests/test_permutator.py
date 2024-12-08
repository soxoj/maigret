import pytest
from maigret.permutator import Permute


def test_gather_strict():
    elements = {'a': 1, 'b': 2}
    permute = Permute(elements)
    result = permute.gather(method="strict")
    expected = {
        'a_b': 1,
        'b_a': 2,
        'a-b': 1,
        'b-a': 2,
        'a.b': 1,
        'b.a': 2,
        'ab': 1,
        'ba': 2,
        '_ab': 1,
        'ab_': 1,
        '_ba': 2,
        'ba_': 2,
    }
    assert result == expected


def test_gather_all():
    elements = {'a': 1, 'b': 2}
    permute = Permute(elements)
    result = permute.gather(method="all")
    expected = {
        'a': 1,
        '_a': 1,
        'a_': 1,
        'b': 2,
        '_b': 2,
        'b_': 2,
        'a_b': 1,
        'b_a': 2,
        'a-b': 1,
        'b-a': 2,
        'a.b': 1,
        'b.a': 2,
        'ab': 1,
        'ba': 2,
        '_ab': 1,
        'ab_': 1,
        '_ba': 2,
        'ba_': 2,
    }
    assert result == expected
