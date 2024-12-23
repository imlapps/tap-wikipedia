from pydantic import AnyUrl, BaseModel

from tap_wikipedia.models.types import StrippedString as Abstract
from tap_wikipedia.models.types import StrippedString as Title


class AbstractInfo(BaseModel):
    """Pydantic Model to hold the contents extracted from the Wikipedia abstracts dump."""

    title: Title
    url: AnyUrl
    abstract: Abstract
    imageUrl: AnyUrl | None = None
