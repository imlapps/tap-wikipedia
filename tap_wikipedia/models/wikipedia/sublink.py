from typing import Annotated

from pydantic import BaseModel, Field

# A tiny type for string fields in Sublink
Sublink = Annotated[
    str, Field(json_schema_extra={"strip_whitespace": "True"})
]


class Sublink(BaseModel):
    """Pydantic Model to hold a sublink of a Wikipedia Article."""

    anchor: Sublink | None = None
    link: Sublink | None = None
