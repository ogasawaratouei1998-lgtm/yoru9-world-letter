"""Shared seven-day publication-date preflight; not an approval decision."""
import re
from datetime import datetime, timedelta

def valid_recent_reported(raw, now):
    """Seven-day lookback matches the publisher's existing current-news limit."""
    if not isinstance(raw,str) or not re.fullmatch(r"\d{4}[-.]\d{2}[-.]\d{2}",raw):return False
    try:reported=datetime.strptime(raw.replace(".","-"),"%Y-%m-%d").date()
    except ValueError:return False
    return now.date()-timedelta(days=7)<=reported<=now.date()

