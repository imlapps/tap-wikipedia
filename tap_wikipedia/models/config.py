from typing import Annotated
from appdirs import user_cache_dir
from pydantic import BaseModel, Field
from tap_wikipedia.models.types import SubsetSpecification, EnrichmentType

# A custom data type for str fields in Config
ConfigStringType = Annotated[
    str, Field(json_schema_extra={"strip_whitespace": "True"})
]


class Config(BaseModel):
    abstracts_dump_url: ConfigStringType = Field(
        default="https://dumps.wikimedia.org/enwiki/latest/enwiki-latest-abstract.xml.gz")
    cache_path: ConfigStringType = Field(
        default=user_cache_dir("abstracts", "tap-wikipedia"))
    enrichment_type: tuple[EnrichmentType, ...]
    subset_specification: tuple[SubsetSpecification, ...]
