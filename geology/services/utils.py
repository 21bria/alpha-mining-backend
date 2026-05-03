# utils.py
from datetime import date,datetime
from django.db.models import Max
import json
from datetime import datetime, date
from django.db.models import Max
from datetime import datetime

def clean_string(value):
    """Menghapus spasi berlebih dari string, jika bukan string, biarkan apa adanya."""
    return value.strip() if isinstance(value, str) else value

def safe_float(value):
    try:
        return float(value) if value and str(value).replace('.', '', 1).isdigit() else 0.0
    except:
        return 0.0
    
def validate_year(value):
    if value is None:  # Jika None, kembalikan None
        return None
    try:
        year = int(value)
        if 1900 <= year <= datetime.now().year:  # Pastikan dalam rentang wajar
            return year
    except ValueError:
        pass
    return None

def validate_month(value):
    if value is None:  # Jika None, kembalikan None
        return None
    try:
        month = int(value)
        if 1 <= month <= 12:  # Pastikan bulan antara 1 dan 12
            return month
    except ValueError:
        pass
    return None

class NaNEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, float) and (obj != obj):  # Memeriksa NaN
            return None
        return super().default(obj)

def get_month_label(month_number):
    month_labels = {
        1: 'Jan', 2: 'Feb', 3: 'Mar', 4: 'Apr',
        5: 'May', 6: 'Jun', 7: 'Jul', 8: 'Aug',
        9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dec'
    }
    return month_labels.get(month_number, '')

