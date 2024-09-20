

from pydantic import BaseModel
from tap_wikipedia.models.types import CategoryStringType


class Category(BaseModel):
    """Pydantic Model to hold a category of a Wikipedia Article."""

    text: CategoryStringType | None = None
    link: CategoryStringType | None = None
