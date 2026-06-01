"""
Fetch FIFA World Cup 2026 results from football-data.org (free tier).
API key is required — get one free at https://www.football-data.org/client/register
The WC 2026 competition ID will be published before the tournament.

Fallback: if the API fails or the competition isn't available yet,
the admin can always enter results manually.
"""
import requests
from django.conf import settings

FDORG_KEY = getattr(settings, 'FOOTBALL_DATA_API_KEY', '')
FDORG_BASE = 'https://api.football-data.org/v4'
WC2026_ID = getattr(settings, 'WC2026_COMPETITION_ID', 2000)  # update when confirmed


def _headers():
    return {'X-Auth-Token': FDORG_KEY}


def fetch_match_result(fd_match_id: int) -> dict | None:
    """
    Fetch a single match from football-data.org by its match ID.
    Returns a dict with keys: home_score, away_score, status, penalties
    or None on error.
    """
    if not FDORG_KEY:
        return None
    try:
        r = requests.get(f'{FDORG_BASE}/matches/{fd_match_id}', headers=_headers(), timeout=8)
        if r.status_code != 200:
            return None
        data = r.json()
        score = data.get('score', {})
        ft = score.get('fullTime', {})
        pen = score.get('penalties', {})
        return {
            'status': data.get('status'),
            'home': ft.get('home'),
            'away': ft.get('away'),
            'pen_home': pen.get('home'),
            'pen_away': pen.get('away'),
            'hubo_penales': pen.get('home') is not None,
        }
    except Exception:
        return None


def fetch_wc_matches() -> list[dict]:
    """
    Fetch all matches for WC 2026. Returns a list of match dicts.
    """
    if not FDORG_KEY:
        return []
    try:
        r = requests.get(
            f'{FDORG_BASE}/competitions/{WC2026_ID}/matches',
            headers=_headers(),
            timeout=10
        )
        if r.status_code != 200:
            return []
        return r.json().get('matches', [])
    except Exception:
        return []
