# analytics/services/bot/parsers/natural_parser.py

FILLER_WORDS = [
    "alpha",
    "tolong",
    "bisa",
    "dong",
    "donk",
    "please",
    "can you",
    "could you",
    "buatkan",
    "buat",
    "kasih",
    "minta",
]


def normalize_message(message):
    text = message.lower().strip()

    for word in FILLER_WORDS:
        text = text.replace(word, " ")

    return " ".join(text.split())