from pydantic import BaseModel

from tap_wikipedia.models.wikipedia import AbstractInfo, Category, ExternalLink, Sublink


class Record(BaseModel):
    """Pydantic Model to hold the contents of a Wikipedia record."""

    abstract_info: AbstractInfo
    categories: tuple[Category, ...] | None = None
    external_links: tuple[ExternalLink, ...] | None = None
    sublinks: tuple[Sublink, ...] | None = None
