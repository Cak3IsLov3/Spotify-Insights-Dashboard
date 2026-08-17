import time
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app, _sessions, _oauth_states
from app.spotify_client import SpotifyClient
from app.models import GenreCount


# ── Fixtures ─────────────────────────────────────────────────────

MOCK_PROFILE = {
    "id": "testuser",
    "display_name": "Test User",
    "email": "test@example.com",
    "country": "NL",
    "product": "premium",
    "images": [{"url": "https://example.com/avatar.jpg", "height": 300, "width": 300}],
}

MOCK_ARTISTS = {
    "items": [
        {
            "id": f"artist_{i}",
            "name": f"Artist {i}",
            "genres": ["pop", "rock"] if i % 2 == 0 else ["hip-hop", "rap"],
            "popularity": 50 + i * 5,
            "images": [{"url": f"https://example.com/artist_{i}.jpg"}],
        }
        for i in range(10)
    ]
}

MOCK_TRACKS = {
    "items": [
        {
            "id": f"track_{i}",
            "name": f"Track {i}",
            "artists": [{"id": "a1", "name": f"Artist {i}"}],
            "album": {
                "id": f"album_{i}",
                "name": f"Album {i}",
                "images": [{"url": f"https://example.com/album_{i}.jpg"}],
            },
            "popularity": 60 + i,
            "preview_url": None,
            "external_urls": {"spotify": f"https://open.spotify.com/track/{i}"},
        }
        for i in range(10)
    ]
}


def _create_test_session() -> str:
    """Create a test session and return the signed cookie value."""
    from itsdangerous import URLSafeSerializer
    from app.config import SECRET_KEY

    session_id = "test-session-id"
    client = SpotifyClient(
        access_token="fake-token",
        refresh_token="fake-refresh",
        expires_at=time.time() + 3600,
    )
    _sessions[session_id] = client
    serializer = URLSafeSerializer(SECRET_KEY)
    return serializer.dumps(session_id)


@pytest.fixture
def signed_cookie():
    token = _create_test_session()
    yield token
    _sessions.pop("test-session-id", None)


# ── Tests ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_home_redirects_to_login():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/", follow_redirects=False)
    assert resp.status_code == 200
    assert "Connect with Spotify" in resp.text


@pytest.mark.asyncio
async def test_login_redirects_to_spotify():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/login", follow_redirects=False)
    assert resp.status_code == 307
    assert "accounts.spotify.com/authorize" in resp.headers["location"]


@pytest.mark.asyncio
async def test_callback_invalid_state():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/callback?code=abc&state=invalid")
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_api_me_requires_auth():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_api_me_returns_profile(signed_cookie):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        with patch.object(SpotifyClient, "_get", new_callable=AsyncMock, return_value=MOCK_PROFILE):
            resp = await ac.get("/api/me", cookies={"session_token": signed_cookie})
    assert resp.status_code == 200
    data = resp.json()
    assert data["display_name"] == "Test User"


@pytest.mark.asyncio
async def test_api_top_artists(signed_cookie):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        with patch.object(SpotifyClient, "_get", new_callable=AsyncMock, return_value=MOCK_ARTISTS):
            resp = await ac.get("/api/top/artists", cookies={"session_token": signed_cookie})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["short_term"]) == 10
    assert data["short_term"][0]["name"] == "Artist 0"


@pytest.mark.asyncio
async def test_api_insights(signed_cookie):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        with patch.object(SpotifyClient, "_get", new_callable=AsyncMock, return_value=MOCK_ARTISTS):
            resp = await ac.get("/api/insights", cookies={"session_token": signed_cookie})
    assert resp.status_code == 200
    data = resp.json()
    assert "top_genres" in data
    assert "obscurity_score" in data
    assert data["genre_diversity"] > 0


@pytest.mark.asyncio
async def test_logout(signed_cookie):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/logout", cookies={"session_token": signed_cookie}, follow_redirects=False)
    assert resp.status_code == 302
    assert "test-session-id" not in _sessions


def test_genre_count_model():
    gc = GenreCount(name="pop", count=5)
    assert gc.name == "pop"
    assert gc.count == 5
