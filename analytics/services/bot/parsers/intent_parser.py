# parsers/intent_parser.py

GREETING_KEYWORDS = [
    "halo",
    "hallo",
    "hai",
    "hi",
    "hello",
    "pagi",
    "siang",
    "sore",
    "malam",
    "selamat pagi",
    "selamat siang",
    "selamat sore",
    "selamat malam",
]


ALLOWED_KEYWORDS = [
    "produksi", "production", "plan", "actual", "achievement", "target",
    "grade", "quality", "kualitas", "ni", "fe", "mgo", "sio2", "sm", "samples",
    "barging", "tongkang", "barge", "vessel", "selling", "shipment", "loading", "hauling", "waybills",
    "inventory", "stock", "dome", "stockpile", "blending", "high grade", "low grade",
    "kpi", "productivity", "fuel", "solar", "bbm", "equipment", "unit", "fleet",
    "hujan", "rainfall", "rain", "cuaca", "weather", "slippery", "rainy",
    "coa", "roa", "mral","blending", "blend", "campur", "mixing", "high grade", "low grade",
]


def is_greeting(message):
    text = message.lower().strip().replace(",", "")

    return text in GREETING_KEYWORDS or text in [
        "halo alpha",
        "hallo alpha",
        "hai alpha",
        "hi alpha",
        "hello alpha",
    ]


def is_allowed_question(message):
    text = message.lower()

    # tetap harus ada domain mining
    return any(keyword in text for keyword in ALLOWED_KEYWORDS)


def detect_intent(message):
    text = message.lower()

    domains = set()

    # WEATHER / RAINFALL prioritas
    if any(k in text for k in [
        "data hujan",
        "hujan",
        "rainfall",
        "rain data",
        "rain",
        "cuaca",
        "weather",
        "slippery",
        "rainy",
    ]):
        return "weather_review", ["weather"]

    # BLENDING harus prioritas
    if any(k in text for k in [
        "blending",
        "blend",
        "campur",
        "mixing",
        "high grade",
        "low grade",
        "dome",
        "stockpile",
    ]):
        return "blending_review", ["blending"]

    domains = set()

    if any(k in text for k in [
        "inventory",
        "stock inventory",
        "inventory stock",
        "inventory movement",
    ]):
        domains.add("inventory")
        

    # if any(k in text for k in [
    #     "inventory", "stock", "dome", "stockpile"
    # ]):
    #     domains.add("inventory")
  

    if any(k in text for k in [
        "selling", "shipment", "barging", "tongkang", "barge",
        "vessel", "loading", "jetty",
    ]):
        domains.add("barging")

    if any(k in text for k in [
        "grade", "quality", "kualitas", "ni", "fe", "mgo",
        "sio2", "coa", "roa", "sample", "samples",
    ]):
        domains.add("quality")

    if any(k in text for k in [
        "produksi", "production", "plan", "actual",
        "achievement", "tonnage", "target", "output",
    ]):
        domains.add("production")

    if any(k in text for k in [
        "fuel", "solar", "bbm", "liter", "fuel ratio", "consumption",
    ]):
        domains.add("fuel")

    if any(k in text for k in [
        "equipment", "unit", "fleet", "ma", "pa", "ua", "eu",
        "breakdown", "bd", "standby", "idle",
    ]):
        domains.add("equipment")

    # if any(k in text for k in [
    #     "weather", "cuaca", "rainfall", "rain", "hujan", "slippery",
    # ]):
    #     domains.add("weather")
 

    domains = list(domains)

    if len(domains) > 1:
        return "operational_analysis", domains

    if "inventory" in domains:
        return "inventory_review", domains

    if "barging" in domains:
        return "barging_review", domains

    if "quality" in domains:
        return "quality_review", domains

    if "fuel" in domains:
        return "fuel_review", domains

    if "equipment" in domains:
        return "equipment_review", domains

    if "weather" in domains:
        return "weather_review", domains
    
    if "blending" in domains:
        return "blending_review", domains

    return "production_review", ["production"]