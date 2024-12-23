from pydantic import BaseModel

from tap_wikipedia.models.types import StrippedString as CategoryStringType


class Category(BaseModel):
    """Pydantic Model to hold a category of a Wikipedia article."""

    text: CategoryStringType | None = None
    link: CategoryStringType | None = None
