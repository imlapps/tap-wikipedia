from typing import Annotated
from pydantic import Field

# A tiny type for string fields in a Wikipedia Article's URL
WebPageUrl = Annotated[str, Field(min_length=1, json_schema_extra={
    "strip_whitespace": "True"})]
