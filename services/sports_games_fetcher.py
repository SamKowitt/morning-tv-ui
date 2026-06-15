from dataclasses import dataclass
from datetime import datetime, timedelta
from urllib.error import URLError
from urllib.parse import urlencode
from zoneinfo import ZoneInfo
import json
import ssl
import urllib.request


LOCAL_TIMEZONE = ZoneInfo("America/New_York")

MLB_SCHEDULE_ENDPOINT = "https://statsapi.mlb.com/api/v1/schedule"

ESPN_SCOREBOARD_ENDPOINTS = {
    "NFL": "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard",
    "NBA": "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard",
}

LEAGUE_META = {
    "MLB": {
        "emoji": "⚾",
        "priority": 1,
        "active_months": {3, 4, 5, 6, 7, 8, 9, 10, 11},
    },
    "NFL": {
        "emoji": "🏈",
        "priority": 2,
        "active_months": {8, 9, 10, 11, 12, 1, 2},
    },
    "NBA": {
        "emoji": "🏀",
        "priority": 3,
        "active_months": {10, 11, 12, 1, 2, 3, 4, 5, 6},
    },
}

MLB_FAVORITES = {"NYY", "LAD", "CLE"}
NFL_FAVORITES = {"CAR", "CLE"}
NBA_FAVORITES = {"CHA", "CHI"}

EXCLUDED_ESPN_STATUS_TYPES = {
    "STATUS_CANCELED",
    "STATUS_POSTPONED",
    "STATUS_DELAYED",
    "STATUS_SUSPENDED",
    "STATUS_FORFEIT",
    "STATUS_UNNECESSARY",
}

EXCLUDED_MLB_STATUS_WORDS = {
    "cancelled",
    "canceled",
    "postponed",
    "suspended",
}


@dataclass
class SportsGame:
    matchup: str
    time: str
    detail: str = ""


@dataclass
class SportsLeague:
    emoji: str
    league: str
    games: list[SportsGame]


def is_league_active_by_month(league, current_date=None):
    if current_date is None:
        current_date = datetime.now(LOCAL_TIMEZONE).date()

    return current_date.month in LEAGUE_META[league]["active_months"]


def is_mlb_expanded_month(current_date=None):
    if current_date is None:
        current_date = datetime.now(LOCAL_TIMEZONE).date()

    return current_date.month in {9, 10, 11}


def make_placeholder_league(league, message):
    return SportsLeague(
        emoji=LEAGUE_META[league]["emoji"],
        league=league,
        games=[
            SportsGame(
                matchup="No games scheduled",
                time="—",
                detail=message,
            )
        ],
    )


def fetch_json(url, timeout=12):
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "MorningTVUI/1.0",
            "Accept": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read()

        return json.loads(raw.decode("utf-8"))

    except URLError as error:
        message = str(error)

        if "CERTIFICATE_VERIFY_FAILED" not in message:
            raise

        print("SSL certificate verification failed. Retrying with relaxed SSL context...")

        relaxed_context = ssl._create_unverified_context()

        with urllib.request.urlopen(
            request,
            timeout=timeout,
            context=relaxed_context,
        ) as response:
            raw = response.read()

        return json.loads(raw.decode("utf-8"))


def parse_datetime(value):
    if not value:
        return None

    try:
        if value.endswith("Z"):
            value = value.replace("Z", "+00:00")

        parsed = datetime.fromisoformat(value)

        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=ZoneInfo("UTC"))

        return parsed.astimezone(LOCAL_TIMEZONE)
    except Exception:
        return None


def format_datetime_time(value):
    parsed = parse_datetime(value)

    if parsed is None:
        return "TBD"

    return parsed.strftime("%-I:%M %p")


def get_game_local_date(value):
    parsed = parse_datetime(value)

    if parsed is None:
        return None

    return parsed.date()


# -----------------------------
# MLB
# -----------------------------

def get_mlb_team_info(team_obj):
    team = team_obj.get("team", {}) if isinstance(team_obj, dict) else {}

    abbreviation = (
        team.get("abbreviation")
        or team.get("fileCode")
        or team.get("teamCode")
        or ""
    ).upper()

    name = (
        abbreviation
        or team.get("teamName")
        or team.get("name")
        or "TBD"
    )

    return abbreviation, name


def build_mlb_schedule_url(date_from, date_to):
    query = {
        "sportId": 1,
        "startDate": f"{date_from:%Y-%m-%d}",
        "endDate": f"{date_to:%Y-%m-%d}",
        "hydrate": "team,probablePitcher,linescore,broadcasts(all)",
    }

    return f"{MLB_SCHEDULE_ENDPOINT}?{urlencode(query)}"


def get_mlb_game_status(game):
    status = game.get("status", {})

    return (
        status.get("detailedState")
        or status.get("abstractGameState")
        or ""
    )


def should_include_mlb_game(game):
    status = get_mlb_game_status(game).lower()

    for excluded_word in EXCLUDED_MLB_STATUS_WORDS:
        if excluded_word in status:
            return False

    teams = game.get("teams", {})
    away = teams.get("away", {})
    home = teams.get("home", {})

    return bool(away and home)


def get_mlb_team_abbreviations(game):
    teams = game.get("teams", {})
    away = teams.get("away", {})
    home = teams.get("home", {})

    away_abbr, _ = get_mlb_team_info(away)
    home_abbr, _ = get_mlb_team_info(home)

    return {away_abbr, home_abbr}


def is_mlb_favorite_game(game):
    return bool(get_mlb_team_abbreviations(game) & MLB_FAVORITES)


def build_mlb_matchup(game):
    teams = game.get("teams", {})
    away = teams.get("away", {})
    home = teams.get("home", {})

    away_abbr, away_name = get_mlb_team_info(away)
    home_abbr, home_name = get_mlb_team_info(home)

    away_display = away_abbr or away_name
    home_display = home_abbr or home_name

    status = get_mlb_game_status(game).lower()

    away_score = away.get("score")
    home_score = home.get("score")

    if away_score is not None and home_score is not None and "final" in status:
        try:
            away_score_number = int(away_score)
            home_score_number = int(home_score)
        except Exception:
            away_score_number = away_score
            home_score_number = home_score

        away_winner = " W" if away_score_number > home_score_number else ""
        home_winner = " W" if home_score_number > away_score_number else ""

        return (
            f"{away_display} {away_score}{away_winner}\n"
            f"{home_display} {home_score}{home_winner}"
        )

    if away_score is not None and home_score is not None:
        if "in progress" in status or "live" in status:
            return f"{away_display} {away_score} @ {home_display} {home_score}"

    return f"{away_display} @ {home_display}"


def format_mlb_time(game):
    status = get_mlb_game_status(game)
    lowered = status.lower()

    if "final" in lowered:
        return "FINAL"

    if "in progress" in lowered or "live" in lowered:
        linescore = game.get("linescore", {})
        inning = linescore.get("currentInningOrdinal", "")
        half = linescore.get("inningHalf", "")

        if inning and half:
            return f"{half} {inning}"

        return "LIVE"

    return format_datetime_time(game.get("gameDate"))


def build_mlb_detail(game):
    teams = game.get("teams", {})
    away = teams.get("away", {})
    home = teams.get("home", {})

    away_pitcher = away.get("probablePitcher", {})
    home_pitcher = home.get("probablePitcher", {})

    away_pitcher_name = away_pitcher.get("fullName", "")
    home_pitcher_name = home_pitcher.get("fullName", "")

    if away_pitcher_name and home_pitcher_name:
        return f"{away_pitcher_name} vs. {home_pitcher_name}"

    broadcasts = game.get("broadcasts", [])
    names = []

    for broadcast in broadcasts[:2]:
        name = broadcast.get("name")
        if name:
            names.append(name)

    if names:
        return "TV: " + ", ".join(names)

    return ""


def mlb_base_sort_key(game):
    status = get_mlb_game_status(game).lower()

    if "in progress" in status or "live" in status:
        priority = 0
    elif "scheduled" in status or "preview" in status or "pre-game" in status:
        priority = 1
    elif "final" in status:
        priority = 2
    else:
        priority = 3

    parsed = parse_datetime(game.get("gameDate"))

    if parsed is None:
        parsed = datetime.max.replace(tzinfo=LOCAL_TIMEZONE)

    return priority, parsed


def mlb_sort_key(game):
    favorite_priority = 0 if is_mlb_favorite_game(game) else 1
    base_priority, parsed = mlb_base_sort_key(game)

    return favorite_priority, base_priority, parsed


def fetch_mlb_games(max_games_per_league=3):
    today = datetime.now(LOCAL_TIMEZONE).date()
    date_from = today
    date_to = today

    url = build_mlb_schedule_url(date_from, date_to)

    print(f"Fetching MLB games from MLB Stats API for today's date only: {today:%Y-%m-%d}...")
    print(url)

    data = fetch_json(url)

    all_games = []

    for date_block in data.get("dates", []):
        all_games.extend(date_block.get("games", []) or [])

    usable_games = []

    for game in all_games:
        if not should_include_mlb_game(game):
            continue

        game_date = get_game_local_date(game.get("gameDate"))

        if game_date != today:
            continue

        usable_games.append(game)

    if is_mlb_expanded_month(today):
        filtered_games = usable_games
        print("MLB expanded month rule active. Showing favorite teams first, then other MLB games from today.")
    else:
        filtered_games = [
            game for game in usable_games
            if is_mlb_favorite_game(game)
        ]
        print("MLB selected-team rule active. Showing Yankees, Dodgers, and Guardians games from today only.")

    if not filtered_games:
        print("MLB is active, but no selected MLB games were found for today.")
        return []

    filtered_games = sorted(filtered_games, key=mlb_sort_key)
    filtered_games = filtered_games[:max_games_per_league]

    games = []

    for game in filtered_games:
        games.append(
            SportsGame(
                matchup=build_mlb_matchup(game),
                time=format_mlb_time(game),
                detail=build_mlb_detail(game),
            )
        )

    return games


# -----------------------------
# ESPN: NFL / NBA
# -----------------------------

def build_espn_scoreboard_url(league, date_value):
    endpoint = ESPN_SCOREBOARD_ENDPOINTS[league]

    query = {
        "limit": 100,
        "dates": f"{date_value:%Y%m%d}",
    }

    return f"{endpoint}?{urlencode(query)}"


def get_espn_status_name(event):
    return (
        event.get("status", {})
        .get("type", {})
        .get("name", "")
    )


def get_espn_status_detail(event):
    status = event.get("status", {})
    status_type = status.get("type", {})

    return (
        status_type.get("detail")
        or status_type.get("shortDetail")
        or ""
    )


def get_espn_competitors(event):
    competitions = event.get("competitions", [])

    if not competitions:
        return []

    return competitions[0].get("competitors", []) or []


def should_include_espn_event(event):
    status_name = get_espn_status_name(event)

    if status_name in EXCLUDED_ESPN_STATUS_TYPES:
        return False

    return len(get_espn_competitors(event)) >= 2


def get_espn_team_name(competitor):
    team = competitor.get("team", {})

    return (
        team.get("abbreviation")
        or team.get("shortDisplayName")
        or team.get("displayName")
        or "TBD"
    )


def get_espn_team_abbreviations(event):
    abbreviations = set()

    for competitor in get_espn_competitors(event):
        team = competitor.get("team", {})
        abbr = (team.get("abbreviation") or "").upper()

        if abbr:
            abbreviations.add(abbr)

    return abbreviations


def is_espn_favorite_game(event, league):
    teams = get_espn_team_abbreviations(event)

    if league == "NFL":
        return bool(teams & NFL_FAVORITES)

    if league == "NBA":
        return bool(teams & NBA_FAVORITES)

    return False


def get_espn_home_away(event):
    home = None
    away = None

    for competitor in get_espn_competitors(event):
        home_away = competitor.get("homeAway")

        if home_away == "home":
            home = competitor
        elif home_away == "away":
            away = competitor

    return home, away


def build_espn_matchup(event):
    home, away = get_espn_home_away(event)

    if home and away:
        home_name = get_espn_team_name(home)
        away_name = get_espn_team_name(away)

        status_name = get_espn_status_name(event)

        away_score = away.get("score", "")
        home_score = home.get("score", "")

        if status_name == "STATUS_FINAL" and away_score != "" and home_score != "":
            try:
                away_score_number = int(away_score)
                home_score_number = int(home_score)
            except Exception:
                away_score_number = away_score
                home_score_number = home_score

            away_winner = " W" if away_score_number > home_score_number else ""
            home_winner = " W" if home_score_number > away_score_number else ""

            return (
                f"{away_name} {away_score}{away_winner}\n"
                f"{home_name} {home_score}{home_winner}"
            )

        if status_name in ["STATUS_IN_PROGRESS", "STATUS_HALFTIME"]:
            if away_score != "" and home_score != "":
                return f"{away_name} {away_score} @ {home_name} {home_score}"

        return f"{away_name} @ {home_name}"

    competitors = get_espn_competitors(event)
    names = [get_espn_team_name(competitor) for competitor in competitors]

    if len(names) >= 2:
        return f"{names[0]} vs {names[1]}"

    return event.get("shortName") or event.get("name") or "Game TBD"


def format_espn_game_time(event):
    status_name = get_espn_status_name(event)
    status_detail = get_espn_status_detail(event)

    if status_name == "STATUS_IN_PROGRESS":
        return status_detail or "LIVE"

    if status_name == "STATUS_FINAL":
        return "FINAL"

    if status_name == "STATUS_HALFTIME":
        return "HALF"

    return format_datetime_time(event.get("date"))


def build_espn_detail(event):
    status_name = get_espn_status_name(event)
    status_detail = get_espn_status_detail(event)

    if status_name in ["STATUS_IN_PROGRESS", "STATUS_HALFTIME"]:
        return status_detail or "Live"

    competitions = event.get("competitions", [])

    if not competitions:
        return ""

    broadcasts = competitions[0].get("broadcasts", [])
    names = []

    for broadcast in broadcasts[:2]:
        media = broadcast.get("media", {})
        short_name = media.get("shortName") or media.get("name")

        if short_name:
            names.append(short_name)

    if names:
        return "TV: " + ", ".join(names)

    return ""


def espn_base_sort_key(event):
    status_name = get_espn_status_name(event)

    priority = {
        "STATUS_IN_PROGRESS": 0,
        "STATUS_HALFTIME": 0,
        "STATUS_SCHEDULED": 1,
        "STATUS_FINAL": 2,
    }.get(status_name, 3)

    parsed = parse_datetime(event.get("date"))

    if parsed is None:
        parsed = datetime.max.replace(tzinfo=LOCAL_TIMEZONE)

    return priority, parsed


def espn_sort_key(event, league):
    favorite_priority = 0 if is_espn_favorite_game(event, league) else 1
    base_priority, parsed = espn_base_sort_key(event)

    return favorite_priority, base_priority, parsed


def fetch_espn_events_for_day(league, date_value):
    url = build_espn_scoreboard_url(league, date_value)

    print(f"Fetching {league} games from ESPN for {date_value:%Y-%m-%d}...")
    print(url)

    data = fetch_json(url)

    return data.get("events", []) or []


def fetch_espn_games(league, max_games_per_league=3):
    today = datetime.now(LOCAL_TIMEZONE).date()

    if league == "NFL":
        lookahead_days = 7
        print("NFL date rule active. Checking games within the next 7 days.")
    else:
        lookahead_days = 1
        print(f"{league} date rule active. Checking today's games only.")

    all_events = []

    for day_offset in range(lookahead_days):
        date_value = today + timedelta(days=day_offset)

        try:
            all_events.extend(fetch_espn_events_for_day(league, date_value))
        except Exception as error:
            print(f"{league} fetch failed for {date_value:%Y-%m-%d}: {error}")

    usable_events = []

    for event in all_events:
        if not should_include_espn_event(event):
            continue

        event_date = get_game_local_date(event.get("date"))

        if league == "NBA" and event_date != today:
            continue

        if league == "NFL":
            if event_date is None:
                continue

            if event_date < today or event_date > today + timedelta(days=6):
                continue

        usable_events.append(event)

    if not usable_events:
        print(f"{league} is active by month, but no usable {league} games were found for the allowed date range.")
        return []

    usable_events = sorted(
        usable_events,
        key=lambda event: espn_sort_key(event, league),
    )

    usable_events = usable_events[:max_games_per_league]

    games = []

    for event in usable_events:
        games.append(
            SportsGame(
                matchup=build_espn_matchup(event),
                time=format_espn_game_time(event),
                detail=build_espn_detail(event),
            )
        )

    return games


# -----------------------------
# Public fetch entry point
# -----------------------------

def fetch_games_for_league(league, max_games_per_league=3):
    try:
        if league == "MLB":
            games = fetch_mlb_games(max_games_per_league=max_games_per_league)
        else:
            games = fetch_espn_games(
                league=league,
                max_games_per_league=max_games_per_league,
            )

        if games:
            return SportsLeague(
                emoji=LEAGUE_META[league]["emoji"],
                league=league,
                games=games,
            )

        if league == "NFL":
            message = "No selected-team or NFL games found in the next 7 days"
        elif league == "MLB":
            message = "No selected-team MLB games found today"
        else:
            message = "No selected-team or NBA games found today"

        return make_placeholder_league(
            league,
            message=message,
        )

    except Exception as error:
        print(f"{league} games fetch failed: {error}")

        return make_placeholder_league(
            league,
            message="Schedule unavailable",
        )


def fetch_current_sports_games(max_games_per_league=3):
    today = datetime.now(LOCAL_TIMEZONE).date()

    print(f"Checking active sports leagues for month {today.month}...")

    leagues = []

    for league in ["MLB", "NFL", "NBA"]:
        if not is_league_active_by_month(league, today):
            print(f"{league} skipped. Month {today.month} is outside active months.")
            continue

        print(f"{league} is active by month rule. Adding league to panel.")

        league_data = fetch_games_for_league(
            league=league,
            max_games_per_league=max_games_per_league,
        )

        leagues.append(league_data)

    leagues = sorted(
        leagues,
        key=lambda item: LEAGUE_META.get(item.league, {}).get("priority", 99),
    )

    print(f"Loaded active sports leagues: {[league.league for league in leagues]}")

    return leagues