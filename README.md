# weather_api

Django REST API for weather forecasts. Fetches data from [OpenWeatherMap OneCall API 3.0](https://openweathermap.org/api/one-call-3), caches results in the database, and exposes a single authenticated endpoint.

Solution for the test [task](https://drive.google.com/file/d/1CbmddgSXVzDiVMMhDKNM7yLQPxWf5Wyp/view).

## Requirements

- Python >= 3.12
- OpenWeatherMap account with [OneCall API 3.0](https://openweathermap.org/api/one-call-3) subscription (free tier available)

## Environment variables

### Required

| Variable | Description |
|----------|-------------|
| `SECRET_KEY` | Django secret key. Generate one at [djecrety.ir](https://djecrety.ir/) |
| `WEATHER_API_KEY` | OpenWeatherMap API key |

### Optional

| Variable | Default | Description |
|----------|---------|-------------|
| `DEBUG` | `False` | Django debug mode |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1` | Comma-separated list of allowed hosts |
| `CSRF_TRUSTED_ORIGINS` | `http://localhost` | Comma-separated list of trusted origins |
| `WEATHER_CACHE_TTL_MINUTES` | `10` | How long (in minutes) weather data is cached in DB before re-fetching |
| `WEATHER_API_TIMEOUT` | `10` | Timeout in seconds for requests to OpenWeatherMap |
| `WEATHER_THROTTLE_RATE` | `60/minute` | API rate limit per authenticated user |

### Database (optional, defaults to SQLite)

| Variable | Description |
|----------|-------------|
| `DB_ENGINE` | Django DB engine (e.g. `django.db.backends.postgresql`) |
| `DB_NAME` | Database name |
| `DB_USER` | Database user |
| `DB_PASSWORD` | Database password |
| `DB_HOST` | Database host |
| `DB_PORT` | Database port |

## Local setup

```bash
# 1. Clone the repo
git clone <repo-url>
cd weather-api

# 2. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set environment variables (see options below)

# 5. Apply migrations
python manage.py migrate

# 6. Start the development server
python manage.py runserver
```

The API will be available at `http://localhost:8000`.

### Setting environment variables

The project reads environment variables from the shell. There are several ways to provide them:

**Option A — export in the current shell session** (simplest, resets on terminal close):

```bash
export SECRET_KEY="your-secret-key-here"
export WEATHER_API_KEY="your-openweathermap-api-key"
export DEBUG=True
```

**Option B — inline before the command** (one-off runs):

```bash
SECRET_KEY="your-secret-key-here" WEATHER_API_KEY="your-api-key" python manage.py runserver
```

**Option C — `.env` file + manual sourcing** (persists across sessions without extra tools):

```bash
# Create the file once
cat > .env << 'EOF'
SECRET_KEY="your-secret-key-here"
WEATHER_API_KEY="your-openweathermap-api-key"
DEBUG=True
EOF

# Source it before running any manage.py command
source <(grep -v '^#' .env | sed 's/^/export /')
```

## Generating a test user

The project includes a management command to create a user and print their API token:

```bash
python manage.py create_test_user
```

Optional arguments:

| Argument | Description |
|----------|-------------|
| `--username USERNAME` | Set a specific username (auto-generated if omitted) |
| `--superuser` | Create a superuser instead of a regular user |

Example output:

```
------------------------------------------------
  User created successfully
------------------------------------------------
  Username  : user_3f9a1c2b
  Password  : xK8!mRpL2@nQvZ4w
  Token     : 9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b
------------------------------------------------
  curl example:
  curl -H "Authorization: Token 9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b" "http://localhost:8000/api/v1/weather-forecasts/?lat=50.45&lon=30.52&data_type=current"
------------------------------------------------
```

## API reference

### Authentication

All endpoints require token authentication. Pass the token in the `Authorization` header:

```
Authorization: Token <your-token>
```

### Rate limiting

Default: **60 requests per minute** per user (configurable via `WEATHER_THROTTLE_RATE`).

---

### GET /api/v1/weather-forecasts/

Returns weather data for the given coordinates and data type. Results are cached in the database and reused until the TTL expires (`WEATHER_CACHE_TTL_MINUTES`, default 10 minutes).

#### Query parameters

| Parameter | Type | Required | Constraints | Description |
|-----------|------|----------|-------------|-------------|
| `lat` | decimal | Yes | -90 to 90 | Latitude |
| `lon` | decimal | Yes | -180 to 180 | Longitude |
| `data_type` | string | Yes | `current`, `minutely`, `hourly`, `daily` | Type of weather data to return |

#### Success response — 200 OK

```json
{
  "id": 1,
  "lat": "50.450000",
  "lon": "30.520000",
  "data_type": "current",
  "fetched_at": "2026-03-10T12:00:00Z",
  "weather_data": {
    "lat": 50.45,
    "lon": 30.52,
    "timezone": "Europe/Kyiv",
    "timezone_offset": 7200,
    "current": {
      "dt": 1741608000,
      "temp": 5.2,
      "feels_like": 2.1,
      "humidity": 78,
      "weather": [{ "id": 800, "main": "Clear", "description": "clear sky", "icon": "01d" }]
    }
  }
}
```

The shape of `weather_data` depends on `data_type` and matches the OpenWeatherMap OneCall API 3.0 response.

#### Error responses

| Status | Cause | Response body |
|--------|-------|---------------|
| `400 Bad Request` | Missing or invalid query parameter | `{"lat": ["This field is required."]}` |
| `401 Unauthorized` | Missing or invalid token | `{"detail": "Authentication credentials were not provided."}` |
| `429 Too Many Requests` | Rate limit exceeded | `{"detail": "Request was throttled. Expected available in N seconds."}` |
| `502 Bad Gateway` | Weather API authentication error, server error, or connectivity issue | `{"detail": "Weather service is temporarily unavailable. Please try again later."}` |
| `503 Service Unavailable` | Weather API rate limit exceeded | `{"detail": "Weather service is temporarily unavailable. Please try again later."}` |

## Examples

### Get current weather for Kyiv

```bash
curl -X GET \
  -H "Authorization: Token 9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b" \
  "http://localhost:8000/api/v1/weather-forecasts/?lat=50.45&lon=30.52&data_type=current"
```

### Get hourly forecast for Lviv

```bash
curl -X GET \
  -H "Authorization: Token 9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b" \
  "http://localhost:8000/api/v1/weather-forecasts/?lat=49.84&lon=24.03&data_type=hourly"
```

### Get daily forecast for Odesa

```bash
curl -X GET \
  -H "Authorization: Token 9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b" \
  "http://localhost:8000/api/v1/weather-forecasts/?lat=46.48&lon=30.73&data_type=daily"
```

### Missing required parameter — 400

```bash
curl -X GET \
  -H "Authorization: Token 9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b" \
  "http://localhost:8000/api/v1/weather-forecasts/?lat=50.45&lon=30.52"
# Response: {"data_type": ["This field is required."]}
```

### No token — 401

```bash
curl -X GET \
  "http://localhost:8000/api/v1/weather-forecasts/?lat=50.45&lon=30.52&data_type=current"
# Response: {"detail": "Authentication credentials were not provided."}
```

### Invalid coordinate range — 400

```bash
curl -X GET \
  -H "Authorization: Token 9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b" \
  "http://localhost:8000/api/v1/weather-forecasts/?lat=200&lon=30.52&data_type=current"
# Response: {"lat": ["Ensure this value is less than or equal to 90."]}
```

## Running tests

```bash
python manage.py test
```

## Possible improvements

- **Geospatial cache clustering.** Cache lookups use exact coordinate matching. In practice, coordinates `50.450001` and `50.450000` represent the same weather zone but produce separate cache entries. Rounding coordinates to a fixed precision (e.g. 2 decimal places, ~1 km grid) or using geospatial proximity queries (e.g. PostGIS `ST_DWithin`) would significantly improve cache hit rate. This was intentionally left out as over-engineering for the current scope.
- **Application-level cache (Redis).** Weather data is currently cached only in the database. Adding Redis as a cache backend (via `django-redis`) would reduce DB query latency on hot coordinates and is a natural next step if the service receives high traffic.
- **Background cache refresh.** The current implementation fetches fresh data synchronously on a cache miss, which adds latency to that request. A background task (Celery + periodic beat) could pre-warm or refresh cache entries before they expire.
- **Bulk endpoint.** A single request can only fetch data for one coordinate pair. A batch endpoint accepting multiple locations would reduce round-trips for clients that need weather for several cities.
