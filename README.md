# football-intelligence-api
Football prediction and odds API built with FastAPI, PostgreSQL, Redis, and modular provider adapters.

## Features
- API-Football provider integration using the official RapidAPI authentication model
- The Odds API integration using the official key-based authentication model
- Independent provider health checks and status tracking
- Fixture synchronization and odds normalization
- PostgreSQL-backed storage for provider metrics and sync results
- Redis-backed caching to limit unnecessary requests
- Administrator status API for provider health and quota tracking

## Environment configuration
This project reads environment variables from a local `.env` file or your deployment environment.

Example:
```bash
cp .env.example .env
```

Then edit `.env` and set your keys:
```bash
API_FOOTBALL_KEY=your_api_football_key
ODDS_API_KEY=your_odds_api_key
DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/football_intelligence
REDIS_URL=redis://localhost:6379/0
APP_ENV=development
DEBUG=false
```

### Local development
1. Create and activate a Python virtual environment.
2. Install dependencies:
```bash
python -m pip install -U pip
python -m pip install -e .[dev]
```
3. Run the application:
```bash
uvicorn app.main:app --reload
```

### Production deployment
Set the same variables in your deployment platform environment (Docker, Render, Railway, Kubernetes secrets, etc.). Do not commit real keys to source control. Use secret managers or environment injection.

Important security rules:
- Never log raw API credentials.
- Never expose provider keys in API responses.
- Never include keys in frontend payloads.
- Validate that values are set before external requests are made.

## Provider integrations

### API-Football
- Auth method: `x-rapidapi-key` header and `x-rapidapi-host` header
- Base URL: `https://api-football-v1.p.rapidapi.com/v3`
- Example health check request: `/v3/status`

### The Odds API
- Auth method: `api_key` query parameter
- Base URL: `https://api.the-odds-api.com/v4`
- Example health check request: `/v4/sports`

## Admin status endpoint
Once the API is running, the administrator endpoint is available at:
- `GET /admin/integrations`

This returns provider name, connection status, last successful synchronization, last failed request, quota, and success/failure counts without exposing any credential values.

## Testing
Run the automated test suite with:
```bash
pytest
```

The suite includes:
- mocked provider request tests
- security tests that verify raw keys are never exposed
- optional live connection checks that only run when credentials are present

Do not treat mocked tests as successful live API verification. Live requests require real credentials and are skipped automatically when the environment variables are unavailable.
