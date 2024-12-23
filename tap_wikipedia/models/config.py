from pathlib import Path
from typing import Annotated

from appdirs import user_cache_dir
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings
from tap_wikipedia.models.types import EnrichmentType, SubsetSpecification


class Config(BaseSettings):
    """A Pydantic Model to hold configuration values of tap-wikipedia."""

    abstracts_dump_url: Annotated[
        str,
        Field(
            min_length=1,
            default="https://dumps.wikimedia.org/enwiki/latest/enwiki-latest-abstract.xml.gz",
            validation_alias="abstracts-dump-url",
        ),
    ]
    cache_directory_path: Annotated[
        Path,
        Field(
            default=Path(user_cache_dir("abstracts", "tap-wikipedia")),
            validation_alias="cache-directory-path",
        ),
    ]
    enrichments: tuple[EnrichmentType, ...] | None = None
    subset_specifications: Annotated[
        tuple[SubsetSpecification, ...] | None,
        Field(validation_alias="subset-specifications"),
    ] = None
    clean_wikipedia_title: bool = True

    @field_validator("cache_directory_path", mode="before")
    @classmethod
    def convert_to_path(cls, cache_directory_str: str) -> Path:
        return Path(cache_directory_str)
