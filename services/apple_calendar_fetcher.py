from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import caldav


ICLOUD_CALDAV_URL = "https://caldav.icloud.com/"
LOCAL_TIMEZONE = ZoneInfo("America/New_York")


@dataclass
class AppleCalendarEvent:
    title: str
    when_text: str
    starts_today: bool
    start_datetime: datetime | None = None
    end_datetime: datetime | None = None
    all_day: bool = False


def normalize_datetime(value):
    if value is None:
        return None, False

    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=LOCAL_TIMEZONE)
        return value.astimezone(LOCAL_TIMEZONE), False

    if isinstance(value, date):
        return datetime.combine(value, time.min, tzinfo=LOCAL_TIMEZONE), True

    return None, False


def format_when_text(start_dt, all_day):
    if start_dt is None:
        return "Upcoming"

    now = datetime.now(LOCAL_TIMEZONE)
    today = now.date()
    event_date = start_dt.date()

    if event_date == today:
        if all_day:
            return "Today"
        return f"Today {start_dt.strftime('%-I:%M %p')}"

    tomorrow = today + timedelta(days=1)

    if event_date == tomorrow:
        if all_day:
            return "Tomorrow"
        return f"Tomorrow {start_dt.strftime('%-I:%M %p')}"

    if all_day:
        return start_dt.strftime("%a, %b %-d")

    return start_dt.strftime("%a, %b %-d %-I:%M %p")


def event_from_caldav_object(event_object):
    instance = event_object.vobject_instance
    vevent = instance.vevent

    title = str(getattr(vevent, "summary", "") or "").strip()

    if hasattr(vevent, "summary"):
        title = str(vevent.summary.value or "").strip()

    if not title:
        title = "Calendar event"

    raw_start = getattr(vevent, "dtstart", None)
    raw_end = getattr(vevent, "dtend", None)

    start_value = raw_start.value if raw_start is not None else None
    end_value = raw_end.value if raw_end is not None else None

    start_dt, start_all_day = normalize_datetime(start_value)
    end_dt, end_all_day = normalize_datetime(end_value)

    all_day = start_all_day or end_all_day
    today = datetime.now(LOCAL_TIMEZONE).date()

    return AppleCalendarEvent(
        title=title,
        when_text=format_when_text(start_dt, all_day),
        starts_today=bool(start_dt and start_dt.date() == today),
        start_datetime=start_dt,
        end_datetime=end_dt,
        all_day=all_day,
    )



# -----------------------------
# Built-in U.S. holidays
# -----------------------------

def nth_weekday_of_month(year, month, weekday, occurrence):
    current = date(year, month, 1)
    days_until_weekday = (weekday - current.weekday()) % 7
    return current + timedelta(days=days_until_weekday + (occurrence - 1) * 7)


def last_weekday_of_month(year, month, weekday):
    if month == 12:
        current = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        current = date(year, month + 1, 1) - timedelta(days=1)

    while current.weekday() != weekday:
        current -= timedelta(days=1)

    return current


def observed_federal_holiday(actual_date):
    if actual_date.weekday() == 5:
        return actual_date - timedelta(days=1)

    if actual_date.weekday() == 6:
        return actual_date + timedelta(days=1)

    return actual_date


def make_builtin_holiday_event(title, holiday_date):
    start_dt = datetime.combine(
        holiday_date,
        time.min,
        tzinfo=LOCAL_TIMEZONE,
    )

    return AppleCalendarEvent(
        title=title,
        when_text=format_when_text(start_dt, True),
        starts_today=(holiday_date == datetime.now(LOCAL_TIMEZONE).date()),
        start_datetime=start_dt,
        end_datetime=start_dt + timedelta(days=1),
        all_day=True,
    )


def built_in_us_holidays(start_date, end_date):
    """
    Returns major U.S. holidays plus Mother's Day and Father's Day.
    The returned range is inclusive.
    """
    if start_date > end_date:
        return []

    holiday_dates = []

    for year in range(start_date.year, end_date.year + 1):
        fixed_holidays = [
            ("New Year's Day", date(year, 1, 1)),
            ("Juneteenth", date(year, 6, 19)),
            ("Independence Day", date(year, 7, 4)),
            ("Veterans Day", date(year, 11, 11)),
            ("Christmas Day", date(year, 12, 25)),
        ]

        for title, actual_date in fixed_holidays:
            holiday_dates.append((title, actual_date))

            observed_date = observed_federal_holiday(actual_date)
            if observed_date != actual_date:
                holiday_dates.append((f"{title} (Observed)", observed_date))

        holiday_dates.extend([
            (
                "Martin Luther King Jr. Day",
                nth_weekday_of_month(year, 1, 0, 3),
            ),
            (
                "Presidents Day",
                nth_weekday_of_month(year, 2, 0, 3),
            ),
            (
                "Mother's Day",
                nth_weekday_of_month(year, 5, 6, 2),
            ),
            (
                "Memorial Day",
                last_weekday_of_month(year, 5, 0),
            ),
            (
                "Father's Day",
                nth_weekday_of_month(year, 6, 6, 3),
            ),
            (
                "Labor Day",
                nth_weekday_of_month(year, 9, 0, 1),
            ),
            (
                "Columbus Day",
                nth_weekday_of_month(year, 10, 0, 2),
            ),
            (
                "Thanksgiving Day",
                nth_weekday_of_month(year, 11, 3, 4),
            ),
        ])

    events = [
        make_builtin_holiday_event(title, holiday_date)
        for title, holiday_date in holiday_dates
        if start_date <= holiday_date <= end_date
    ]

    events.sort(key=lambda item: item.start_datetime)
    return events


def fetch_dashboard_calendar_events(
    apple_id_email="",
    app_specific_password="",
    days_ahead=14,
    max_events=8,
):
    """
    Combines built-in U.S. holidays with optional iCloud calendar events.
    Holidays remain available even if iCloud is not configured or fails.
    """
    days_ahead = max(1, min(int(days_ahead or 14), 60))

    now = datetime.now(LOCAL_TIMEZONE)
    start_date = now.date()
    end_date = start_date + timedelta(days=days_ahead)

    events = built_in_us_holidays(start_date, end_date)

    apple_id_email = str(apple_id_email or "").strip()
    app_specific_password = str(app_specific_password or "").strip()

    if apple_id_email and app_specific_password:
        try:
            icloud_events = fetch_icloud_calendar_events(
                apple_id_email=apple_id_email,
                app_specific_password=app_specific_password,
                days_ahead=days_ahead,
                max_events=100,
            )
            events.extend(icloud_events)
        except Exception as error:
            print(f"iCloud calendar unavailable; showing built-in holidays only: {error}")
    else:
        print("Apple Calendar is not configured; showing built-in U.S. holidays only.")

    unique_events = []
    seen = set()

    for event in sorted(
        events,
        key=lambda item: item.start_datetime
        or datetime.max.replace(tzinfo=LOCAL_TIMEZONE),
    ):
        event_key = (
            str(event.title or "").strip().lower(),
            event.start_datetime.date() if event.start_datetime else None,
        )

        if event_key in seen:
            continue

        seen.add(event_key)
        unique_events.append(event)

    print(f"Loaded {len(unique_events)} combined calendar/holiday event(s).")

    return unique_events[:max_events]

def fetch_icloud_calendar_events(apple_id_email, app_specific_password, days_ahead=14, max_events=8):
    apple_id_email = str(apple_id_email or "").strip()
    app_specific_password = str(app_specific_password or "").strip()

    if not apple_id_email:
        raise ValueError("Apple ID email is missing.")

    if not app_specific_password:
        raise ValueError("Apple app-specific password is missing.")

    days_ahead = int(days_ahead or 14)

    if days_ahead < 1:
        days_ahead = 1

    if days_ahead > 60:
        days_ahead = 60

    now = datetime.now(LOCAL_TIMEZONE)
    start = datetime.combine(now.date(), time.min, tzinfo=LOCAL_TIMEZONE)
    end = start + timedelta(days=days_ahead)

    client = caldav.DAVClient(
        url=ICLOUD_CALDAV_URL,
        username=apple_id_email,
        password=app_specific_password,
    )

    principal = client.principal()
    calendars = principal.calendars()

    events = []

    for calendar in calendars:
        try:
            calendar_events = calendar.date_search(
                start=start,
                end=end,
                expand=True,
            )

            for event_object in calendar_events:
                try:
                    event = event_from_caldav_object(event_object)

                    if event.start_datetime is None:
                        continue

                    if event.start_datetime < start - timedelta(days=1):
                        continue

                    events.append(event)

                except Exception as event_error:
                    print(f"Could not parse iCloud calendar event: {event_error}")

        except Exception as calendar_error:
            print(f"Could not read one iCloud calendar: {calendar_error}")

    events.sort(key=lambda item: item.start_datetime or datetime.max.replace(tzinfo=LOCAL_TIMEZONE))

    print(f"Loaded {len(events)} iCloud calendar event(s).")

    return events[:max_events]
