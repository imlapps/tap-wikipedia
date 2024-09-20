from collections.abc import Callable, Iterable
from tap_wikipedia.models import wikipedia
from functools import reduce


def pipe(
    *,
    pipe_callables: tuple[
        Callable[[Iterable[wikipedia.Record]], Iterable[wikipedia.Record]], ...
    ],
    initializer: Iterable[wikipedia.Record],
) -> Iterable[wikipedia.Record]:
    """ 
        Yield from a pipe of callables. 

        Callables in `pipe_callables` are piped in linear order, from left-to-right.

        The input to the first callable of the pipe is `initializer`.
    """
    yield from reduce(lambda x, y: y(x), pipe_callables, initializer)
