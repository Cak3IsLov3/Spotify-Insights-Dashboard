import secrets
from collections import Counter
from dataclasses import asdict

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from itsdangerous import URLSafeSerializer

from app.config import SECRET_KEY
from app.models import GenreCount
from app.spotify_client import SpotifyClient, SpotifyAuthError

app = FastAPI(title="Spotify Insights Dashboard")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Simple in-memory session store: {session_id: SpotifyClient}
_sessions: dict[str, SpotifyClient] = {}
_serializer = URLSafeSerializer(SECRET_KEY)

# Pending OAuth states (state -> True)
_oauth_states: dict[str, bool] = {}


def _get_session_id(request: Request) -> str | None:
    token = request.cookies.get("session_token")
    if not token:
        return None
    try:
        return _serializer.loads(token)
    except Exception:
        return None


def _get_client(request: Request) -> SpotifyClient:
    sid = _get_session_id(request)
    if not sid or sid not in _sessions:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return _sessions[sid]


# ── Auth routes ──────────────────────────────────────────────────

@app.get("/login")
async def login():
    state = secrets.token_urlsafe(32)
    _oauth_states[state] = True
    url = SpotifyClient.build_authorize_url(state)
    return RedirectResponse(url)


@app.get("/callback")
async def callback(request: Request, code: str = "", state: str = "", error: str = ""):
    if error:
        return templates.TemplateResponse(
            "login.html", {"request": request, "error": f"Spotify error: {error}"}
        )
    if state not in _oauth_states:
        raise HTTPException(status_code=400, detail="Invalid state parameter (CSRF)")
    _oauth_states.pop(state, None)

    try:
        tokens = await SpotifyClient.exchange_code(code)
    except SpotifyAuthError as e:
        raise HTTPException(status_code=400, detail=str(e))

    client = SpotifyClient(
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        expires_at=tokens["expires_at"],
    )
    session_id = secrets.token_urlsafe(32)
    _sessions[session_id] = client

    response = RedirectResponse("/dashboard", status_code=302)
    signed = _serializer.dumps(session_id)
    response.set_cookie(
        "session_token", signed, httponly=True, samesite="lax", max_age=3600
    )
    return response


@app.get("/logout")
async def logout(request: Request):
    sid = _get_session_id(request)
    if sid:
        _sessions.pop(sid, None)
    response = RedirectResponse("/", status_code=302)
    response.delete_cookie("session_token")
    return response


# ── API routes ───────────────────────────────────────────────────

@app.get("/api/me")
async def api_me(request: Request):
    client = _get_client(request)
    profile = await client.get_profile()
    return asdict(profile)


@app.get("/api/top/artists")
async def api_top_artists(request: Request):
    client = _get_client(request)
    short = await client.get_top_artists("short_term")
    medium = await client.get_top_artists("medium_term")
    long = await client.get_top_artists("long_term")
    return {
        "short_term": [asdict(a) for a in short],
        "medium_term": [asdict(a) for a in medium],
        "long_term": [asdict(a) for a in long],
    }


@app.get("/api/top/tracks")
async def api_top_tracks(request: Request):
    client = _get_client(request)
    short = await client.get_top_tracks("short_term")
    medium = await client.get_top_tracks("medium_term")
    long = await client.get_top_tracks("long_term")
    return {
        "short_term": [asdict(t) for t in short],
        "medium_term": [asdict(t) for t in medium],
        "long_term": [asdict(t) for t in long],
    }


@app.get("/api/insights")
async def api_insights(request: Request):
    client = _get_client(request)
    artists = await client.get_top_artists("medium_term", limit=50)

    # Genre frequency
    all_genres: list[str] = []
    for a in artists:
        all_genres.extend(a.genres)
    genre_counts = Counter(all_genres).most_common(15)
    top_genres = [asdict(GenreCount(name=g, count=c)) for g, c in genre_counts]

    # Obscurity score (average popularity — lower = more obscure)
    popularities = [a.popularity for a in artists]
    obscurity_score = sum(popularities) / len(popularities) if popularities else 0

    # Mainstream percentage
    mainstream = sum(1 for p in popularities if p > 70)
    mainstream_pct = (mainstream / len(popularities) * 100) if popularities else 0

    return {
        "top_genres": top_genres,
        "obscurity_score": round(obscurity_score, 1),
        "genre_diversity": len(set(all_genres)),
        "total_artists_analyzed": len(artists),
        "mainstream_percentage": round(mainstream_pct, 1),
    }


# ── Page routes ──────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    sid = _get_session_id(request)
    if sid and sid in _sessions:
        return RedirectResponse("/dashboard")
    return templates.TemplateResponse("login.html", {"request": request})


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    client = _get_client(request)
    profile = await client.get_profile()
    return templates.TemplateResponse(
        "dashboard.html", {"request": request, "profile": profile}
    )
