from typing import Annotated

from pydantic import Field

# A tiny type for a Wikipedia article's title.
Title = Annotated[str, Field(json_schema_extra={"strip_whitespace": "True"})]
