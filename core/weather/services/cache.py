from datetime import timedelta

from django.conf import settings
from django.utils.timezone import now

from core.weather.enums import WeatherDataType
from core.weather.models import WeatherCache

from .owm_client import fetch_weather_from_api


def get_cached_weather(lat: float, lon: float, data_type: WeatherDataType) -> WeatherCache | None:
    """Return a fresh cached record for the given coordinates and data type, or None if expired/missing."""
    threshold = now() - timedelta(minutes=settings.WEATHER_CACHE_TTL_MINUTES)
    try:
        return WeatherCache.objects.filter(
            lat=lat,
            lon=lon,
            data_type=data_type,
            fetched_at__gte=threshold,
        ).get()
    except WeatherCache.DoesNotExist:
        return None


def save_weather_cache(lat, lon, data_type, weather_data) -> WeatherCache:
    instance, _ = WeatherCache.objects.update_or_create(
        lat=lat,
        lon=lon,
        data_type=data_type,
        defaults={'weather_data': weather_data, 'fetched_at': now()},
    )
    return instance


def get_weather(lat: float, lon: float, data_type: WeatherDataType) -> WeatherCache:
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
