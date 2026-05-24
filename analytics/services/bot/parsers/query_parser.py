from .intent_parser import detect_intent
from .date_parser import parse_date
from .natural_parser import normalize_message


def parse_query(message):
    text = normalize_message(message)

    intent, domains = detect_intent(text)
    params = parse_date(text)

    return {
        "intent": intent,
        "domains": domains,
        "params": params
    }