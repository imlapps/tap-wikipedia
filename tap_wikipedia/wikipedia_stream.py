from __future__ import annotations

from singer_sdk import Stream


class WikipediaStream(Stream):
    """Tap stream for Wikipedia data."""

    def __init__(self, *args, **kwargs):  # noqa: ANN002, ANN003
        super().__init__(*args, **kwargs)
