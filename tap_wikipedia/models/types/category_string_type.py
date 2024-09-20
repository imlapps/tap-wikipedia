from typing import Annotated

from pydantic import Field

# A tiny type for str fields in wikipedia.Category.
CategoryStringType = Annotated[
    str, Field(json_schema_extra={"strip_whitespace": "True"})
]
