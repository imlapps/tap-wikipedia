from typing import Annotated

from pydantic import Field

# Tiny type to remove leading and trailing whitespace from a string.
StrippedString = Annotated[str, Field(json_schema_extra={"strip_whitespace": "True"})]
