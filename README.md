# Spotify Insights Dashboard

A FastAPI web app that visualises your personal Spotify listening data — top artists, top tracks, favourite genres and fun stats like your "obscurity score".

## Features

- **OAuth 2.0 Authorization Code Flow** — secure server-side login with Spotify
- **Top Artists & Tracks** — view your most-listened across three time periods (4 weeks, 6 months, all-time)
- **Genre Insights** — doughnut chart of your top genres
- **Obscurity Score** — how mainstream (or underground) your taste is
- **Genre Diversity** — number of unique genres in your top artists
- **Responsive Dashboard** — dark-themed UI with Chart.js visualisations

## Screenshots

> _Add screenshots of the login page and dashboard here after running the app._

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI, Uvicorn |
| HTTP Client | httpx (async) |
| Data Models | Python dataclasses |
| Templates | Jinja2 |
| Charts | Chart.js |
| Auth | OAuth 2.0 (Spotify) |
| Tests | pytest, pytest-asyncio |

## OAuth 2.0 Flow

```
User clicks "Login" → FastAPI redirects to Spotify authorize URL
                       (with client_id, scopes, state)
                     ↓
User grants consent on Spotify
                     ↓
Spotify redirects to /callback?code=...&state=...
                     ↓
FastAPI exchanges code for access_token + refresh_token (server-side)
                     ↓
Token stored in signed httpOnly cookie → user sees dashboard
                     ↓
On 401 → automatic refresh with refresh_token
```

## Setup

### 1. Spotify Developer App

1. Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
2. Create a new app
3. Add `http://127.0.0.1:8000/callback` as a Redirect URI
4. Copy Client ID and Client Secret

### 2. Install & Run

```bash
# Clone the repo
git clone https://github.com/YOUR_USERNAME/spotify-insights.git
cd spotify-insights

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your Spotify Client ID and Secret

# Run the app
python run.py
```

Open http://127.0.0.1:8000 and click **Connect with Spotify**.

### 3. Run Tests

```bash
pytest -v
```

## Project Structure

```
spotify-insights/
├── app/
│   ├── __init__.py
│   ├── config.py           # Environment variables & Spotify URLs
│   ├── main.py             # FastAPI app, routes, session management
│   ├── models.py           # Dataclass models for Spotify data
│   └── spotify_client.py   # Async Spotify API client with token refresh
├── static/
│   ├── css/style.css       # Dark-themed responsive styles
│   └── js/dashboard.js     # Chart.js charts & data fetching
├── templates/
│   ├── base.html           # Base template
│   ├── login.html          # Login page
│   └── dashboard.html      # Dashboard with charts
├── tests/
│   └── test_app.py         # Pytest tests with mocked Spotify responses
├── .env.example
├── .gitignore
├── requirements.txt
├── run.py
└── README.md
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Login page (or redirect to dashboard if authenticated) |
| GET | `/login` | Start OAuth flow |
| GET | `/callback` | OAuth callback |
| GET | `/logout` | Clear session |
| GET | `/dashboard` | Main dashboard (HTML) |
| GET | `/api/me` | Current user profile (JSON) |
| GET | `/api/top/artists` | Top artists across 3 time ranges (JSON) |
| GET | `/api/top/tracks` | Top tracks across 3 time ranges (JSON) |
| GET | `/api/insights` | Derived stats: genres, obscurity, diversity (JSON) |

## License

MIT
