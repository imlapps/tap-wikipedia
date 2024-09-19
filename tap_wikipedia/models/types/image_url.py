from typing import Annotated
from pydantic import Field

# A tiny type for string fields in a Wikipedia Article's Image URL
ImageUrl = Annotated[str, Field(min_length=1, json_schema_extra={
    "strip_whitespace": "True"})]
