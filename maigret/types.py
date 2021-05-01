from typing import Callable, List, Dict, Tuple, Any


# search query
QueryDraft = Tuple[Callable, List, Dict]

# options dict
QueryOptions = Dict[str, Any]

# TODO: throw out
QueryResultWrapper = Dict[str, Any]
