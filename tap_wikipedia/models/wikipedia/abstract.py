
from pydantic import BaseModel


from tap_wikipedia.models.wikipedia import Category, ExternalLink, Sublink, AbstractInfo


class Abstract(BaseModel):
    """Pydantic Model to hold the contents of a Wikipedia Abstract."""

    abstract_info: AbstractInfo
    categories: tuple[Category, ...] | None = None
    external_links: tuple[ExternalLink, ...] | None = None
    sublink: tuple[Sublink, ...] | None = None
