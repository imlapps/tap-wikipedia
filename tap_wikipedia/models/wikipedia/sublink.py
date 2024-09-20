from pydantic import BaseModel

from tap_wikipedia.models.types import SublinkStringType


class Sublink(BaseModel):
    """Pydantic Model to hold a sublink of a Wikipedia article."""

    anchor: SublinkStringType | None = None
    link: SublinkStringType | None = None
