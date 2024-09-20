
from pydantic import BaseModel
from tap_wikipedia.models.types import ExternalLinkStringType


class ExternalLink(BaseModel):
    """Pydantic Model to hold the external link of a Wikipedia Article."""

    title: ExternalLinkStringType | None = None
    link: ExternalLinkStringType | None = None
