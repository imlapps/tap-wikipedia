from typing import Annotated

from pydantic import BaseModel, Field

# A custom data type for str fields in ExternalLink
ExternalLinkStringType = Annotated[
    str, Field(json_schema_extra={"strip_whitespace": "True"})
]


class ExternalLink(BaseModel):
    """Pydantic Model to hold an external link of a Wikipedia Article."""

    title: ExternalLinkStringType | None = None
    link: ExternalLinkStringType | None = None
