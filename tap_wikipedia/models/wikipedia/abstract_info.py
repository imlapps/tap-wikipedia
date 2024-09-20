from pydantic import BaseModel

from tap_wikipedia.models.types import Abstract, ImageUrl, Title, WebPageUrl


class AbstractInfo(BaseModel):
    """Pydantic Model to hold the contents extracted from the Wikipedia abstracts dump."""

    title: Title
    url: WebPageUrl
    abstract: Abstract
    imageUrl: ImageUrl | None = None
