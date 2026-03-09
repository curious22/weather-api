from datetime import timedelta

from django.conf import settings
from django.utils.timezone import now

from core.weather.enums import WeatherDataType
from core.weather.models import WeatherCache

from .owm_client import fetch_weather_from_api


def get_cached_weather(lat: float, lon: float, data_type: WeatherDataType) -> WeatherCache | None:
    """Return a fresh cached record for the given coordinates and data type, or None if expired/missing."""
    threshold = now() - timedelta(minutes=settings.WEATHER_CACHE_TTL_MINUTES)
    return WeatherCache.objects.filter(
        lat=lat,
        lon=lon,
        data_type=data_type,
        fetched_at__gte=threshold,
    ).first()


def save_weather_cache(lat: float, lon: float, data_type: WeatherDataType, weather_data: dict) -> WeatherCache:
    """Persist raw API response to the cache and return the saved instance."""
    instance = WeatherCache(lat=lat, lon=lon, data_type=data_type, weather_data=weather_data)
    instance.full_clean()
    instance.save()

    return instance


def get_weather(lat: float, lon: float, data_type: WeatherDataType) -> WeatherCache | None:
    """
    Return weather data for the given coordinates and type.

    Serves from cache if a fresh record exists; otherwise fetches from OWM API,
    saves the result, and returns the new cache entry.
    Raises WeatherAPIError (or subclass) if the API request fails.
    """
    cached = get_cached_weather(lat, lon, data_type)
    if cached:
        return cached

    data = fetch_weather_from_api(lat, lon, data_type)
    instance = save_weather_cache(lat, lon, data_type, data)
    return instance
