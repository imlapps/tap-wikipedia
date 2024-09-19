from pathlib import Path
from typing import Annotated
from appdirs import user_cache_dir
from pydantic import BaseModel, Field, field_validator
from tap_wikipedia.models.types import SubsetSpecification, EnrichmentType


class Config(BaseModel):
    abstracts_dump_url: Annotated[
        str,
        Field(min_length=1,
              default="https://dumps.wikimedia.org/enwiki/latest/enwiki-latest-abstract.xml.gz"
              ),
    ]
    cache_directory_path: Path = Field(
        default=user_cache_dir("abstracts", "tap-wikipedia")
    )
    enrichments: tuple[EnrichmentType, ...]
    subset_specifications: tuple[SubsetSpecification, ...]

    @field_validator("cache_directory_path", mode="before")
    @classmethod
    def convert_to_path(cls, cache_directory_str: str) -> Path:
        return Path(cache_directory_str)
