from typing import Callable, Any, Tuple


# search query
QueryDraft = Tuple[Callable, Any, Any]

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
