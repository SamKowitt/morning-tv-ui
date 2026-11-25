"""MorningUI Game Times V33: six local calendar days, one next game per team.
Uses the existing MLB/ESPN helpers and favorites; retains final scores until 05:00 ET.
"""
from datetime import datetime, timedelta
from threading import RLock
from time import monotonic

_ESPN_DAY_CACHE = {}
_CACHE_LOCK = RLock()
_WEEKDAY = ('Mon', 'Tues', 'Wed', 'Thur', 'Fri', 'Sat', 'Sun')


def _api():
    import services.sports_games_fetcher as source
    return source


def _now():
    s = _api()
    return datetime.now(s.LOCAL_TIMEZONE)


def _fetch_espn_day(league, day, today):
    s = _api()
    key = (league, day)
    # Today and yesterday remain fresh. Future schedules change much less.
    ttl = 45 if day <= today else 900
    with _CACHE_LOCK:
        entry = _ESPN_DAY_CACHE.get(key)
        if entry is not None and monotonic() - entry[0] < ttl:
            return entry[1]
    try:
        events = s.fetch_espn_events_for_day(league, day)
    except Exception:
        if entry is not None and monotonic() - entry[0] < 3600:
            return entry[1]
        raise
    with _CACHE_LOCK:
        _ESPN_DAY_CACHE[key] = (monotonic(), events)
        if len(_ESPN_DAY_CACHE) > 45:
            oldest = min(_ESPN_DAY_CACHE, key=lambda k: _ESPN_DAY_CACHE[k][0])
            _ESPN_DAY_CACHE.pop(oldest, None)
    return events


def _status(league, raw):
    s = _api()
    if league == 'MLB':
        value = s.get_mlb_game_status(raw).lower()
        final = any(k in value for k in ('final', 'game over', 'complete'))
        live = 'in progress' in value or 'live' in value
    else:
        status = s.get_espn_status_name(raw)
        kind = (raw.get('status') or {}).get('type') or {}
        final = status in {'STATUS_FINAL', 'STATUS_FULL_TIME'} or bool(kind.get('completed'))
        live = status in {'STATUS_IN_PROGRESS', 'STATUS_HALFTIME', 'STATUS_END_PERIOD'}
    return live, final


def _identity(league, raw):
    if league == 'MLB':
        return str(raw.get('gamePk') or '')
    return str(raw.get('id') or '')


def _candidate(league, raw, now):
    s = _api()
    if not (s.should_include_mlb_game(raw) if league == 'MLB'
            else s.should_include_espn_event(raw)):
        return None
    start = s.parse_datetime(raw.get('gameDate' if league == 'MLB' else 'date'))
    if start is None:
        return None
    local_day = start.date()
    today = now.date()
    live, final = _status(league, raw)
    keep_yesterday = now.hour < 5 and local_day == today - timedelta(days=1) and final
    within = today <= local_day <= today + timedelta(days=5)
    if not within and not keep_yesterday:
        return None
    if final and not (local_day == today or keep_yesterday):
        return None
    if live and local_day != today:
        return None
    if not final and not live and not within:
        return None
    if league == 'MLB':
        teams = s.get_mlb_team_abbreviations(raw)
    else:
        teams = s.get_espn_team_abbreviations(raw)
    teams = {x.upper() for x in teams if x}
    if not teams:
        return None
    # Live and retained finals outrank the team's next scheduled game.
    category = 0 if live else 1 if final else 2
    return {'raw': raw, 'date': start, 'teams': teams,
            'category': category, 'id': _identity(league, raw)}


def _choose(league, candidates, max_games, favorite_teams, now):
    s = _api()
    ordered = list(s.favorite_teams_for_league(league, favorite_teams))
    favorites = set(ordered)
    expanded = league == 'MLB' and s.is_mlb_expanded_month(now.date())
    if not expanded:
        candidates = [c for c in candidates if c['teams'] & favorites]
    if expanded:
        other = sorted({t for c in candidates for t in c['teams']} - favorites)
        ordered.extend(other)

    selected = []
    used_teams = set()
    used_ids = set()
    for team in ordered:
        if team in used_teams:
            continue
        matching = [c for c in candidates if team in c['teams']]
        # Per team: live/retained final first; otherwise the nearest upcoming.
        matching.sort(key=lambda c: (c['category'],
                                     -c['date'].timestamp() if c['category'] == 1 else c['date'].timestamp()))
        for candidate in matching:
            if candidate['id'] in used_ids:
                used_teams.update(candidate['teams'])
                break
            if candidate['teams'] & used_teams:
                continue
            selected.append(candidate)
            used_teams.update(candidate['teams'])
            used_ids.add(candidate['id'])
            break
        if len(selected) >= max_games:
            break
    # Match the existing panel's live/upcoming/final order for rows.
    selected.sort(key=lambda c: (0 if c['category'] == 0 else 1 if c['category'] == 2 else 2,
                                 c['date']))
    return selected[:max_games]


def _render(league, candidates, max_games, favorites, now):
    s = _api()
    selected = _choose(league, candidates, max_games, favorites, now)
    games = []
    for c in selected:
        raw = c['raw']
        if league == 'MLB':
            matchup = s.build_mlb_matchup(raw)
            clock = s.format_mlb_time(raw)
            detail = s.build_mlb_detail(raw)
            clickable = s.is_mlb_boxscore_clickable(raw)
        else:
            matchup = s.build_espn_matchup(raw)
            clock = s.format_espn_game_time(raw)
            detail = s.build_espn_detail(raw)
            clickable = s.is_espn_boxscore_clickable(raw)
        # A single newline is rendered by the existing QPainter with the same
        # font, color, weight and column as the game's start time.
        if c['category'] == 2 and c['date'].date() != now.date():
            clock = _WEEKDAY[c['date'].weekday()] + '\n' + clock
        game = s.SportsGame(matchup=matchup, time=clock, detail=detail,
                            league=league, game_id=c['id'], is_clickable=clickable)
        # Existing DashboardWindow uses this for 60-second live polling / prefetch.
        game.is_live = c['category'] == 0
        games.append(game)
    return games


def fetch_mlb_games_v33(max_games_per_league=3, favorite_teams=None):
    s = _api()
    now = _now()
    today = now.date()
    first = today - timedelta(days=1) if now.hour < 5 else today
    last = today + timedelta(days=5)
    url = s.build_mlb_schedule_url(first, last)
    data = s.fetch_json(url)
    candidates = [c for block in (data.get('dates') or [])
                  for raw in (block.get('games') or [])
                  if (c := _candidate('MLB', raw, now)) is not None]
    games = _render('MLB', candidates, max_games_per_league, favorite_teams, now)
    print(f'GAME_TIMES_V33 MLB dates={first}..{last} selected={len(games)}', flush=True)
    return games


def fetch_espn_games_v33(league, max_games_per_league=3, favorite_teams=None):
    if league not in {'NFL', 'NBA'}:
        raise ValueError(f'Unexpected ESPN league: {league}')
    now = _now()
    today = now.date()
    first = today - timedelta(days=1) if now.hour < 5 else today
    last = today + timedelta(days=5)
    candidates = []
    errors = []
    for days in range((last - first).days + 1):
        day = first + timedelta(days=days)
        try:
            events = _fetch_espn_day(league, day, today)
            candidates.extend(c for raw in events
                              if (c := _candidate(league, raw, now)) is not None)
        except Exception as exc:
            errors.append(f'{day}: {exc}')
    if errors:
        print(f'GAME_TIMES_V33 {league} fetch errors: {errors[:2]}', flush=True)
        if len(errors) == (last - first).days + 1:
            raise RuntimeError(f'{league} ESPN scoreboard requests all failed')
    games = _render(league, candidates, max_games_per_league, favorite_teams, now)
    print(f'GAME_TIMES_V33 {league} dates={first}..{last} selected={len(games)}', flush=True)
    return games


def install():
    s = _api()
    s.fetch_mlb_games = fetch_mlb_games_v33
    s.fetch_espn_games = fetch_espn_games_v33
    print('GAME_TIMES_V33 installed 6-day selection, 05:00 ET final cutoff, and weekday time labels', flush=True)

