import time
from urllib.parse import urlencode

import httpx

from app.config import (
    SPOTIFY_API_BASE,
    SPOTIFY_AUTH_URL,
    SPOTIFY_CLIENT_ID,
    SPOTIFY_CLIENT_SECRET,
    SPOTIFY_TOKEN_URL,
    SCOPES,
    REDIRECT_URI,
)
from app.models import ArtistItem, TrackItem, UserProfile


class SpotifyAuthError(Exception):
    """Raised when authentication with Spotify fails."""


class SpotifyAPIError(Exception):
    """Raised when a Spotify API call fails."""


class SpotifyClient:
    """Async client for the Spotify Web API with automatic token refresh."""

    def __init__(
        self,
        access_token: str,
        refresh_token: str,
        expires_at: float,
    ):
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.expires_at = expires_at

    # ── Auth helpers ──────────────────────────────────────────────

    @staticmethod
    def build_authorize_url(state: str) -> str:
        params = {
            "client_id": SPOTIFY_CLIENT_ID,
            "response_type": "code",
            "redirect_uri": REDIRECT_URI,
            "scope": SCOPES,
            "state": state,
        }
        return f"{SPOTIFY_AUTH_URL}?{urlencode(params)}"

    @staticmethod
    async def exchange_code(code: str) -> dict:
        """Exchange an authorization code for access + refresh tokens."""
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                SPOTIFY_TOKEN_URL,
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": REDIRECT_URI,
                    "client_id": SPOTIFY_CLIENT_ID,
                    "client_secret": SPOTIFY_CLIENT_SECRET,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
        if resp.status_code != 200:
            raise SpotifyAuthError(f"Token exchange failed: {resp.text}")
        data = resp.json()
        return {
            "access_token": data["access_token"],
            "refresh_token": data.get("refresh_token", ""),
            "expires_at": time.time() + data.get("expires_in", 3600),
        }

    async def _refresh_access_token(self) -> None:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                SPOTIFY_TOKEN_URL,
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": self.refresh_token,
                    "client_id": SPOTIFY_CLIENT_ID,
                    "client_secret": SPOTIFY_CLIENT_SECRET,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
        if resp.status_code != 200:
            raise SpotifyAuthError("Token refresh failed")
        data = resp.json()
        self.access_token = data["access_token"]
        self.expires_at = time.time() + data.get("expires_in", 3600)
        if "refresh_token" in data:
            self.refresh_token = data["refresh_token"]

    @property
    def token_expired(self) -> bool:
        return time.time() >= self.expires_at - 60  # 60s buffer

    async def _ensure_token(self) -> None:
        if self.token_expired:
            await self._refresh_access_token()

    # ── API calls ─────────────────────────────────────────────────

    async def _get(self, path: str, params: dict | None = None) -> dict:
        await self._ensure_token()
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{SPOTIFY_API_BASE}{path}",
                params=params,
                headers={"Authorization": f"Bearer {self.access_token}"},
            )
        if resp.status_code == 401:
            # One retry after refresh
            await self._refresh_access_token()
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{SPOTIFY_API_BASE}{path}",
                    params=params,
                    headers={"Authorization": f"Bearer {self.access_token}"},
                )
        if resp.status_code != 200:
            raise SpotifyAPIError(
                f"Spotify API error {resp.status_code}: {resp.text}"
            )
        return resp.json()

    async def get_profile(self) -> UserProfile:
        data = await self._get("/me")
        return UserProfile.from_dict(data)

    async def get_top_artists(
        self, time_range: str = "medium_term", limit: int = 20
    ) -> list[ArtistItem]:
        data = await self._get(
            "/me/top/artists", {"time_range": time_range, "limit": limit}
        )
        return [ArtistItem.from_dict(item) for item in data.get("items", [])]

    async def get_top_tracks(
        self, time_range: str = "medium_term", limit: int = 20
    ) -> list[TrackItem]:
        data = await self._get(
            "/me/top/tracks", {"time_range": time_range, "limit": limit}
        )
        return [TrackItem.from_dict(item) for item in data.get("items", [])]
