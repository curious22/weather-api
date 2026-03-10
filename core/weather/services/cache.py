from datetime import timedelta
from decimal import Decimal

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


def save_weather_cache(lat: Decimal, lon: Decimal, data_type: WeatherDataType, weather_data: dict) -> WeatherCache:
    """Upsert weather cache entry for the given coordinates and data type."""
    instance, _ = WeatherCache.objects.update_or_create(
        lat=lat,
        lon=lon,
        data_type=data_type,
        defaults={'weather_data': weather_data, 'fetched_at': now()},
    )
    return instance


def get_weather(lat: Decimal, lon: Decimal, data_type: WeatherDataType) -> WeatherCache:
    """
    Return weather data for the given coordinates and type.
    Raises WeatherAPIError (or subclass) if the API request fails.
    """
    cached = get_cached_weather(lat, lon, data_type)
    if cached:
        return cached

    data = fetch_weather_from_api(lat, lon, data_type)
    instance = save_weather_cache(lat, lon, data_type, data)
    return instance
