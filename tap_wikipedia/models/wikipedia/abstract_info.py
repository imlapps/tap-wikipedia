from pydantic import BaseModel

from tap_wikipedia.models.types import (
    StrippedString as Title,
    StrippedString as WebPageUrl,
    StrippedString as Abstract,
    StrippedString as ImageUrl,
)


class AbstractInfo(BaseModel):
    """Pydantic Model to hold the contents extracted from the Wikipedia abstracts dump."""

    title: Title
    url: WebPageUrl
    abstract: Abstract
    imageUrl: ImageUrl | None = None
