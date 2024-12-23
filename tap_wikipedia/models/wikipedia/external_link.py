from pydantic import BaseModel

from tap_wikipedia.models.types import StrippedString as ExternalLinkStringType


class ExternalLink(BaseModel):
    """Pydantic Model to hold the external link of a Wikipedia article."""

    title: ExternalLinkStringType | None = None
    link: ExternalLinkStringType | None = None
