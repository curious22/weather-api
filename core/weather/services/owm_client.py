import logging

import requests
from django.conf import settings
from requests import exceptions

from core.weather.enums import WeatherDataType
from core.weather.exceptions import (
    WeatherAPIAuthError,
    WeatherAPIError,
    WeatherAPIRateLimitError,
    WeatherAPIServerError,
)

logger = logging.getLogger(__name__)

BASE_URL = 'https://api.openweathermap.org/data/3.0/onecall'


def _weather_request(url: str, params: dict) -> dict:
    logger.debug('OpenWeatherMap request. url=%s params=%s', url, params)

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

    if resp.status_code >= 400:
        content_type = resp.headers.get('Content-Type', '')
        try:
            api_message = resp.json().get('message', '') if 'application/json' in content_type else ''
        except ValueError:
            api_message = ''
        detail = f': {api_message}' if api_message else '.'

        if resp.status_code == 401:
            logger.warning('OpenWeatherMap auth error. message=%s url=%s', api_message, url)
            raise WeatherAPIAuthError(f'OpenWeatherMap authentication failed{detail}')
        if resp.status_code == 429:
            logger.warning('OpenWeatherMap rate limit exceeded. message=%s url=%s', api_message, url)
            raise WeatherAPIRateLimitError(f'OpenWeatherMap rate limit exceeded{detail}')
        if resp.status_code >= 500:
            logger.error('OpenWeatherMap server error. status=%s message=%s url=%s', resp.status_code, api_message, url)
            raise WeatherAPIServerError(f'OpenWeatherMap returned server error {resp.status_code}{detail}')
        logger.warning('OpenWeatherMap client error. status=%s message=%s url=%s', resp.status_code, api_message, url)
        raise WeatherAPIError(f'OpenWeatherMap returned error {resp.status_code}{detail}')

    try:
        return resp.json()
    except ValueError as exc:
        logger.error('Failed to decode OpenWeatherMap JSON response. url=%s', url)
        raise WeatherAPIError('OpenWeatherMap returned non-JSON response.') from exc


def fetch_weather_from_api(lat: float, lon: float, data_type: WeatherDataType) -> dict:
    # alerts is always excluded — fetching it is not a supported business use case
    exclude = ','.join([dt for dt in WeatherDataType if dt != data_type] + ['alerts'])
    params = {
        'lat': lat,
        'lon': lon,
        'exclude': exclude,
        'units': 'metric',
        'appid': settings.WEATHER_API_KEY,
    }
    return _weather_request(BASE_URL, params)
