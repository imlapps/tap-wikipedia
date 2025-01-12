WIKI_SUBDIRECTORY = "/wiki/"


WIKIPEDIA_TITLE_PREFIX = "Wikipedia:"


class WikipediaUrl:
    """A class containing Wikipedia-related URLs."""

    BASE_URL = "https://en.wikipedia.org"

    MEDIA_WIKI_API = BASE_URL + "/w/api.php"
    WIKI_SUBDIRECTORY_URL = BASE_URL + WIKI_SUBDIRECTORY
    FEATURED_ARTICLES_URL = WIKI_SUBDIRECTORY_URL + "Wikipedia:Featured_articles"
