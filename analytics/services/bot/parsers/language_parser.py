# parsers/language_parser.py

def detect_language(message):

    text = message.lower()

    english_keywords = [
        "hello",
        "hi",
        "review",
        "production",
        "quality",
        "inventory",
        "weather",
        "please",
        "analyze",
    ]

    if any(k in text for k in english_keywords):
        return "en"

    return "id"