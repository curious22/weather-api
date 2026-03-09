import logging

import requests
from django.conf import settings
from requests import exceptions

from core.weather.enums import WeatherDataType
from core.weather.exceptions import WeatherAPIError

logger = logging.getLogger(__name__)

BASE_URL = 'https://api.openweathermap.org/data/3.0/onecall'

_ALWAYS_EXCLUDE = {'alerts'}
_ALL_DATA_TYPES = {dt.value for dt in WeatherDataType}


def _weather_request(url: str, params: dict) -> dict:
    try:
        resp = requests.get(url, params=params, timeout=settings.WEATHER_API_TIMEOUT)
    except exceptions.Timeout as exc:
        logger.warning('OpenWeatherMap request timed out. url=%s', url)
        raise WeatherAPIError('Request to OpenWeatherMap timed out.') from exc
    except exceptions.ConnectionError as exc:
        logger.warning('OpenWeatherMap connection error. url=%s', url)
        raise WeatherAPIError('Could not connect to OpenWeatherMap.') from exc
    except exceptions.RequestException as exc:
        logger.error('Unexpected error during OpenWeatherMap request. url=%s exc=%s', url, exc)
        raise WeatherAPIError('Unexpected error contacting OpenWeatherMap.') from exc

    if resp.status_code >= 500:
        logger.error('OpenWeatherMap server error. status=%s url=%s', resp.status_code, url)
        raise WeatherAPIError(f'OpenWeatherMap returned server error {resp.status_code}.')
    if resp.status_code >= 400:
        logger.warning('OpenWeatherMap client error. status=%s url=%s', resp.status_code, url)
        raise WeatherAPIError(f'OpenWeatherMap returned client error {resp.status_code}.')

    try:
        return resp.json()
    except ValueError as exc:
        logger.error('Failed to decode OpenWeatherMap JSON response. url=%s', url)
        raise WeatherAPIError('OpenWeatherMap returned non-JSON response.') from exc


def fetch_weather_from_api(lat: float, lon: float, data_type: str) -> dict:
    # Request only data_type; exclude everything else plus types that are never exposed (alerts)
    exclude = ','.join((_ALL_DATA_TYPES - {data_type}) | _ALWAYS_EXCLUDE)
    params = {
        'lat': lat,
        'lon': lon,
        'exclude': exclude,
        'units': 'metric',
        'appid': settings.WEATHER_API_KEY,
    }
    return _weather_request(BASE_URL, params)
