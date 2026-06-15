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
