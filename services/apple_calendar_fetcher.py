from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import caldav
import holidays


ICLOUD_CALDAV_URL = "https://caldav.icloud.com/"
LOCAL_TIMEZONE = ZoneInfo("America/New_York")

RELIGIOUS_HOLIDAY_OPTIONS = [
    ("christian", "Christian"),
    ("jewish", "Jewish"),
    ("islamic", "Islamic"),
    ("hindu", "Hindu"),
    ("buddhist", "Buddhist"),
    ("sikh", "Sikh"),
    ("orthodox_christian", "Orthodox Christian"),
]

RELIGIOUS_SOURCES = {
    "christian": (
        ["VA", "IT", "US"],
        (
            "christmas", "easter", "good friday", "epiphany",
            "assumption", "all saints", "corpus christi",
            "pentecost", "ascension",
        ),
    ),
    "jewish": (
        ["IL"],
        (
            "rosh hashana", "yom kippur", "passover", "pesach",
            "hanukkah", "purim", "sukkot", "shavuot", "tisha",
        ),
    ),
    "islamic": (
        ["SA", "AE"],
        (
            "ramadan", "eid", "islamic", "prophet", "hijri",
            "arafat", "muharram",
        ),
    ),
    "hindu": (
        ["IN"],
        (
            "diwali", "holi", "dussehra", "navratri",
            "janmashtami", "ganesh", "maha shivratri",
        ),
    ),
    "buddhist": (
        ["TH"],
        (
            "buddha", "visakha", "makha", "asalha",
        ),
    ),
    "sikh": (
        ["IN"],
        (
            "guru", "gurpurab", "vaisakhi",
        ),
    ),
    "orthodox_christian": (
        ["GR", "RS", "RO"],
        (
            "orthodox", "easter", "christmas", "epiphany",
            "assumption", "good friday",
        ),
    ),
}


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
        return "Today" if all_day else f"Today {start_dt.strftime('%-I:%M %p')}"

    if event_date == today + timedelta(days=1):
        return "Tomorrow" if all_day else f"Tomorrow {start_dt.strftime('%-I:%M %p')}"

    return (
        start_dt.strftime("%a, %b %-d")
        if all_day
        else start_dt.strftime("%a, %b %-d %-I:%M %p")
    )


def make_holiday_event(title, holiday_date):
    start_dt = datetime.combine(
        holiday_date,
        time.min,
        tzinfo=LOCAL_TIMEZONE,
    )

    return AppleCalendarEvent(
        title=str(title).strip() or "Holiday",
        when_text=format_when_text(start_dt, True),
        starts_today=(holiday_date == datetime.now(LOCAL_TIMEZONE).date()),
        start_datetime=start_dt,
        end_datetime=start_dt + timedelta(days=1),
        all_day=True,
    )


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


def holiday_country_options():
    """
    Curated country picker for the Settings UI.

    The holidays package exposes technical country/provider metadata that is
    not suitable for a human-facing country dropdown.
    """
    return [
        ("US", "United States of America"),
        ("CA", "Canada"),
        ("MX", "Mexico"),
        ("BR", "Brazil"),
        ("AR", "Argentina"),
        ("GB", "United Kingdom"),
        ("IE", "Ireland"),
        ("FR", "France"),
        ("DE", "Germany"),
        ("IT", "Italy"),
        ("ES", "Spain"),
        ("PT", "Portugal"),
        ("NL", "Netherlands"),
        ("BE", "Belgium"),
        ("CH", "Switzerland"),
        ("AT", "Austria"),
        ("SE", "Sweden"),
        ("NO", "Norway"),
        ("DK", "Denmark"),
        ("FI", "Finland"),
        ("PL", "Poland"),
        ("CZ", "Czech Republic"),
        ("GR", "Greece"),
        ("RO", "Romania"),
        ("UA", "Ukraine"),
        ("RU", "Russia"),
        ("IL", "Israel"),
        ("AE", "United Arab Emirates"),
        ("SA", "Saudi Arabia"),
        ("IN", "India"),
        ("CN", "China"),
        ("JP", "Japan"),
        ("KR", "South Korea"),
        ("TH", "Thailand"),
        ("AU", "Australia"),
        ("NZ", "New Zealand"),
        ("ZA", "South Africa"),
    ]

def holidays_for_country(country_code, start_date, end_date):
    country_code = str(country_code or "").strip().upper()

    if not country_code:
        return []

    years = list(range(start_date.year, end_date.year + 1))

    try:
        calendar = holidays.country_holidays(
            country_code,
            years=years,
        )
    except Exception as error:
        print(f"Could not load {country_code} holidays: {error}")
        return []

    events = []

    for holiday_date, title in calendar.items():
        if start_date <= holiday_date <= end_date:
            events.append(make_holiday_event(title, holiday_date))

    return events


def holidays_for_religion(religion_key, start_date, end_date):
    religion_key = str(religion_key or "").strip().lower()
    source = RELIGIOUS_SOURCES.get(religion_key)

    if source is None:
        return []

    source_countries, terms = source
    events = []

    for country_code in source_countries:
        for event in holidays_for_country(
            country_code,
            start_date,
            end_date,
        ):
            normalized_title = event.title.lower()

            if any(term in normalized_title for term in terms):
                events.append(event)

    return events


def fetch_icloud_calendar_events(
    apple_id_email,
    app_specific_password,
    days_ahead=14,
    max_events=100,
):
    apple_id_email = str(apple_id_email or "").strip()
    app_specific_password = str(app_specific_password or "").strip()

    if not apple_id_email:
        raise ValueError("Apple ID email is missing.")

    if not app_specific_password:
        raise ValueError("Apple app-specific password is missing.")

    days_ahead = max(1, min(int(days_ahead or 14), 60))

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

                    if (
                        event.start_datetime is not None
                        and event.start_datetime >= start - timedelta(days=1)
                    ):
                        events.append(event)
                except Exception as event_error:
                    print(f"Could not parse iCloud calendar event: {event_error}")

        except Exception as calendar_error:
            print(f"Could not read one iCloud calendar: {calendar_error}")

    events.sort(
        key=lambda item: item.start_datetime
        or datetime.max.replace(tzinfo=LOCAL_TIMEZONE)
    )

    print(f"Loaded {len(events)} iCloud calendar event(s) for {apple_id_email}.")
    return events[:max_events]


def fetch_dashboard_calendar_events(
    apple_id_email="",
    app_specific_password="",
    days_ahead=14,
    apple_id_email_2="",
    app_specific_password_2="",
    days_ahead_2=14,
    national_holiday_codes=None,
    religious_holiday_keys=None,
    max_events=100,
):
    today = datetime.now(LOCAL_TIMEZONE).date()

    primary_days = max(1, min(int(days_ahead or 14), 60))
    secondary_days = max(1, min(int(days_ahead_2 or 14), 60))
    # National and religious holidays follow Calendar #1's Days Ahead.
    # Calendar #2 controls only the second iCloud account's event range.
    holiday_days = primary_days

    end_date = today + timedelta(days=holiday_days)
    events = []

    country_codes = list(national_holiday_codes or ["US"])
    religion_keys = list(religious_holiday_keys or [])

    for country_code in country_codes:
        events.extend(
            holidays_for_country(
                country_code,
                today,
                end_date,
            )
        )

    for religion_key in religion_keys:
        events.extend(
            holidays_for_religion(
                religion_key,
                today,
                end_date,
            )
        )

    accounts = [
        (
            apple_id_email,
            app_specific_password,
            primary_days,
            "Calendar #1",
        ),
        (
            apple_id_email_2,
            app_specific_password_2,
            secondary_days,
            "Calendar #2",
        ),
    ]

    for email, password, account_days, account_label in accounts:
        if not str(email or "").strip() and not str(password or "").strip():
            continue

        try:
            events.extend(
                fetch_icloud_calendar_events(
                    apple_id_email=email,
                    app_specific_password=password,
                    days_ahead=account_days,
                    max_events=100,
                )
            )
        except Exception as error:
            print(f"{account_label} unavailable: {error}")

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
