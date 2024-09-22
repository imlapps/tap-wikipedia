from collections.abc import Callable, Iterable
from functools import reduce

from tap_wikipedia.models import wikipedia


def pipe(
    *,
    callables: tuple[
        Callable[[Iterable[wikipedia.Record]], Iterable[wikipedia.Record]], ...
    ],
    initializer: Iterable[wikipedia.Record],
) -> Iterable[wikipedia.Record]:
    """
    Yield from a pipe of callables.

    The callables are piped in linear order, from left-to-right.

    The input to the first callable of the pipe is `initializer`.
    """
    yield from reduce(lambda x, y: y(x), callables, initializer)
