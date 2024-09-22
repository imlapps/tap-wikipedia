from tap_wikipedia.models import WIKI_SUBDIRECTORY


class WikipediaUrl:
    """A class containing Wikipedia-related URLs."""

    BASE_URL = "https://en.wikipedia.org"

    MEDIA_WIKI_API = BASE_URL + "/w/api.php"
    WIKI = BASE_URL + WIKI_SUBDIRECTORY
    FEATURED_ARTICLES = WIKI + "/Wikipedia:Featured_articles"
