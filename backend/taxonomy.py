"""Fixed topic taxonomy for meeting classification."""

TOPICS: list[str] = [
    "economic-affairs",
    "foreign-affairs",
    "housing",
    "healthcare",
    "education",
    "justice",
    "migration",
    "climate",
    "infrastructure",
    "culture",
    "defense",
    "social-affairs",
    "finance",
    "digital-affairs",
]

# Dutch display labels for the frontend
TOPIC_LABELS_NL: dict[str, str] = {
    "economic-affairs": "Economie",
    "foreign-affairs": "Buitenlandse zaken",
    "housing": "Wonen",
    "healthcare": "Zorg",
    "education": "Onderwijs",
    "justice": "Justitie",
    "migration": "Migratie",
    "climate": "Klimaat",
    "infrastructure": "Infrastructuur",
    "culture": "Cultuur",
    "defense": "Defensie",
    "social-affairs": "Sociale zaken",
    "finance": "Financiën",
    "digital-affairs": "Digitale zaken",
}
