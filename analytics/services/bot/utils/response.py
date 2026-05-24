# analytics/services/bot/utils/response.py
import json

def json_response_to_dict(response):
    return json.loads(response.content.decode("utf-8"))