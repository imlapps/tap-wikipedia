from __future__ import annotations

from singer_sdk import Stream


class WikipediaStream(Stream):
    """Stream class for wikipedia streams."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
