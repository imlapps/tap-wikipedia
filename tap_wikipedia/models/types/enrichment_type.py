from enum import Enum


class EnrichmentType(Enum):
    """An enum of enrichment types for Wikipedia records."""

    IMAGE_URL = "ImageURL"
    CATEGORY = "Category"
    EXTERNAL_LINK = "ExternalLink"
