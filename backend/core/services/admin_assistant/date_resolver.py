"""
Date Resolver for Admin Data Assistant
Seva Bandhu Platform

Resolves natural-language time expressions to timezone-aware date boundaries.
Reuses the authoritative resolve_date_range from admin_income_analytics_service
to ensure absolute consistency across the platform.
"""

import re
import datetime
from django.utils import timezone
from core.services.admin_income_analytics_service import resolve_date_range


def extract_date_range(query_text: str):
    """
    Scans the query text for time-related phrases and returns:
    (start_dt, end_dt, preset_key, label, remaining_query_text)
    """
    text = query_text.lower().strip()

    # Priority date patterns
    patterns = [
        (r'\b(today|today\'s)\b', 'today'),
        (r'\b(yesterday|yesterday\'s)\b', 'yesterday'),
        (r'\b(this\s+week|current\s+week)\b', 'this_week'),
        (r'\b(last\s+week|previous\s+week|past\s+week)\b', 'last_week'),
        (r'\b(last\s+7\s+days|past\s+7\s+days|7\s+days)\b', 'last_7_days'),
        (r'\b(last\s+30\s+days|past\s+30\s+days|30\s+days)\b', 'last_30_days'),
        (r'\b(this\s+month|current\s+month|this\s+month\'s)\b', 'this_month'),
        (r'\b(last\s+month|previous\s+month|last\s+month\'s|previous\s+month\'s)\b', 'previous_month'),
        (r'\b(this\s+year|current\s+year|this\s+year\'s)\b', 'this_year'),
        (r'\b(last\s+year|previous\s+year)\b', 'last_year'),
        (r'\b(all\s+time|overall|entire\s+history)\b', 'all_time'),
    ]

    matched_preset = None
    cleaned_text = query_text

    for regex, preset in patterns:
        m = re.search(regex, text, re.IGNORECASE)
        if m:
            matched_preset = preset
            # Remove matched date phrase from query so entity/metric parsing is cleaner
            cleaned_text = re.sub(regex, ' ', query_text, flags=re.IGNORECASE)
            break

    if not matched_preset:
        # Default is all_time when looking up an individual entity (e.g. "Ramu's income")
        # or this_month if general query without date
        return None, None, None, None, query_text

    # Custom handling for this_week / last_week
    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = now.replace(hour=23, minute=59, second=59, microsecond=999999)

    if matched_preset == 'this_week':
        start = today_start - datetime.timedelta(days=today_start.weekday())
        return start, today_end, 'this_week', 'This Week', cleaned_text

    elif matched_preset == 'last_week':
        this_week_start = today_start - datetime.timedelta(days=today_start.weekday())
        start = this_week_start - datetime.timedelta(days=7)
        end = this_week_start - datetime.timedelta(microseconds=1)
        return start, end, 'last_week', 'Last Week', cleaned_text

    elif matched_preset == 'last_year':
        first_day_this_year = today_start.replace(month=1, day=1)
        last_day_prev_year = first_day_this_year - datetime.timedelta(days=1)
        first_day_prev_year = last_day_prev_year.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        end_prev_year = last_day_prev_year.replace(hour=23, minute=59, second=59, microsecond=999999)
        return first_day_prev_year, end_prev_year, 'last_year', 'Last Year', cleaned_text

    # Reuse authoritative resolve_date_range for standard presets
    s, e, p, label = resolve_date_range(matched_preset)
    return s, e, p, label, cleaned_text

