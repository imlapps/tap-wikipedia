from enum import Enum


class FeaturedArticleCategory(Enum):
    """
    An enum of featured article categories for Wikipedia records.

    A featured article category is a category of a featured Wikipedia article.

    Categories are obtained from `https://en.wikipedia.org/wiki/Wikipedia:Featured_articles`.
    """

    ART_ARCHITECTURE_AND_ARCHAEOLOGY = "Art,_architecture,_and_archaeology"
    BIOLOGY = "Biology"
    BUSINESS_ECONOMICS_AND_FINANCE = "Business,_economics,_and_finance"
    CHEMISTRY_AND_MINERALOGY = "Chemistry_and_mineralogy"
    COMPUTING = "Computing"
    CULTURE_AND_SOCIETY = "Culture_and_society"
    EDUCATION = "Education"
    ENGINEERING_AND_TECHNOLOGY = "Engineering_and_technology"
    FOOD_AND_DRINK = "Food_and_drink"
    GEOGRAPHY_AND_PLACES = "Geography_and_places"
    GEOLOGY_AND_GEOPHYSICS = "Geology_and_geophysics"
    HEALTH_AND_MEDICINE = "Health_and_medicine"
    HERALDRY_HONOURS_AND_VEXILLOLOGY = "Heraldry,_honours,_and_vexillology"
    HISTORY = "History"
    LANGUAGE_AND_LINGUISTICS = "Language_and_linguistics"
    LAW = "Law"
    LITERATURE_AND_THEATRE = "Literature_and_theatre"
    MATHEMATICS = "Mathematics"
    MEDIA = "Media"
    METEOROLOGY = "Meteorology"
    MUSIC = "Music"
    PHILOSOPHY_AND_PSYCHOLOGY = "Philosophy_and_psychology"
    PHYSICS_AND_ASTRONOMY = "Physics_and_astronomy"
    POLITICS_AND_GOVERNMENT = "Politics_and_government"
    RELIGION_MYSTICISM_AND_MYTHOLOGY = "Religion,_mysticism_and_mythology"
    ROYALTY_AND_NOBILITY = "Royalty_and_nobility"
    SPORT_AND_RECREATION = "Sport_and_recreation"
    TRANSPORT = "Transport"
    VIDEO_GAMING = "Video_gaming"
    WARFARE = "Warfare"
