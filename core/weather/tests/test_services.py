from datetime import timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.db import IntegrityError
from django.test import TestCase, override_settings
from django.utils.timezone import now
from requests import exceptions as req_exc

from core.weather.enums import WeatherDataType
from core.weather.exceptions import (
    WeatherAPIAuthError,
    WeatherAPIError,
    WeatherAPIRateLimitError,
    WeatherAPIServerError,
)
from core.weather.models import WeatherCache
from core.weather.services.cache import get_cached_weather, get_weather, save_weather_cache
from core.weather.services.owm_client import fetch_weather_from_api

LAT, LON = Decimal('47.8387'), Decimal('35.1383')
WEATHER_DATA = {'current': {'temp': 20.5}}


def make_cache_entry(lat=LAT, lon=LON, data_type=WeatherDataType.CURRENT, weather_data=None, fetched_at=None):
    entry = WeatherCache.objects.create(
        lat=lat,
        lon=lon,
        data_type=data_type,
        weather_data=weather_data or WEATHER_DATA,
    )
    if fetched_at is not None:
        WeatherCache.objects.filter(pk=entry.pk).update(fetched_at=fetched_at)
        entry.refresh_from_db()
    return entry


def make_response(status_code=200, json_data=None, content_type='application/json'):
    resp = MagicMock()
    resp.status_code = status_code
    resp.headers = {'Content-Type': content_type}
    if json_data is not None:
        resp.json.return_value = json_data
    else:
        resp.json.side_effect = ValueError('no json')
    return resp


@override_settings(WEATHER_API_KEY='test-key', WEATHER_API_TIMEOUT=5)
@patch('core.weather.services.owm_client.requests.get')
class WeatherRequestErrorsTest(TestCase):
    def test_timeout_raises_weather_api_error(self, mock_get):
        mock_get.side_effect = req_exc.Timeout()
        with self.assertRaises(WeatherAPIError):
            fetch_weather_from_api(LAT, LON, WeatherDataType.CURRENT)

    def test_connection_error_raises_weather_api_error(self, mock_get):
        mock_get.side_effect = req_exc.ConnectionError()
        with self.assertRaises(WeatherAPIError):
            fetch_weather_from_api(LAT, LON, WeatherDataType.CURRENT)

    def test_request_exception_raises_weather_api_error(self, mock_get):
        mock_get.side_effect = req_exc.RequestException()
        with self.assertRaises(WeatherAPIError):
            fetch_weather_from_api(LAT, LON, WeatherDataType.CURRENT)

    def test_401_raises_auth_error(self, mock_get):
        mock_get.return_value = make_response(401, {'message': 'Invalid API key'})
        with self.assertRaises(WeatherAPIAuthError):
            fetch_weather_from_api(LAT, LON, WeatherDataType.CURRENT)

    def test_401_without_json_body_raises_auth_error(self, mock_get):
        mock_get.return_value = make_response(401, content_type='text/html')
        with self.assertRaises(WeatherAPIAuthError):
            fetch_weather_from_api(LAT, LON, WeatherDataType.CURRENT)

    def test_429_raises_rate_limit_error(self, mock_get):
        mock_get.return_value = make_response(429, {'message': 'Rate limit exceeded'})
        with self.assertRaises(WeatherAPIRateLimitError):
            fetch_weather_from_api(LAT, LON, WeatherDataType.CURRENT)

    def test_500_raises_server_error(self, mock_get):
        mock_get.return_value = make_response(500, {'message': 'Internal server error'})
        with self.assertRaises(WeatherAPIServerError):
            fetch_weather_from_api(LAT, LON, WeatherDataType.CURRENT)

    def test_other_4xx_raises_weather_api_error(self, mock_get):
        mock_get.return_value = make_response(404, {'message': 'Not found'})
        with self.assertRaises(WeatherAPIError):
            fetch_weather_from_api(LAT, LON, WeatherDataType.CURRENT)

    def test_non_json_success_response_raises_error(self, mock_get):
        mock_get.return_value = make_response(200, json_data=None)
        with self.assertRaises(WeatherAPIError):
            fetch_weather_from_api(LAT, LON, WeatherDataType.CURRENT)


@override_settings(WEATHER_API_KEY='test-key', WEATHER_API_TIMEOUT=5)
@patch('core.weather.services.owm_client.requests.get')
class FetchWeatherParamsTest(TestCase):
    def test_request_params_are_correct(self, mock_get):
        mock_get.return_value = make_response(200, {})
        fetch_weather_from_api(LAT, LON, WeatherDataType.CURRENT)
        params = mock_get.call_args.kwargs['params']

        self.assertEqual(params['lat'], LAT)
        self.assertEqual(params['lon'], LON)
        self.assertEqual(params['units'], 'metric')
        self.assertEqual(params['appid'], 'test-key')

    def test_success_returns_json(self, mock_get):
        expected = {'current': {'temp': 7.74}}
        mock_get.return_value = make_response(200, expected)
        result = fetch_weather_from_api(LAT, LON, WeatherDataType.CURRENT)
        self.assertEqual(result, expected)

    def test_exclude_contains_all_other_types_and_alerts(self, mock_get):
        mock_get.return_value = make_response(200, {})
        all_types = list(WeatherDataType)

        for data_type in all_types:
            with self.subTest(data_type=data_type):
                fetch_weather_from_api(LAT, LON, data_type)
                params = mock_get.call_args.kwargs['params']
                exclude = params['exclude'].split(',')

                self.assertNotIn(data_type.value, exclude, msg=f'{data_type} should not be excluded')
                for other in all_types:
                    if other != data_type:
                        self.assertIn(other.value, exclude, msg=f'{other} should be excluded')
                self.assertIn('alerts', exclude)

    def test_calls_correct_url(self, mock_get):
        mock_get.return_value = make_response(200, {})
        fetch_weather_from_api(LAT, LON, WeatherDataType.CURRENT)
        call_args = mock_get.call_args
        self.assertEqual('https://api.openweathermap.org/data/3.0/onecall', call_args.args[0])


@override_settings(WEATHER_CACHE_TTL_MINUTES=60)
class GetCachedWeatherTest(TestCase):
    def test_returns_none_when_no_cache(self):
        result = get_cached_weather(LAT, LON, WeatherDataType.CURRENT)
        self.assertIsNone(result)

    def test_returns_fresh_cache_entry(self):
        entry = make_cache_entry()
        result = get_cached_weather(LAT, LON, WeatherDataType.CURRENT)
        self.assertEqual(result.pk, entry.pk)

    def test_returns_none_for_expired_cache(self):
        make_cache_entry(fetched_at=now() - timedelta(minutes=61))
        result = get_cached_weather(LAT, LON, WeatherDataType.CURRENT)
        self.assertIsNone(result)

    def test_returns_none_for_different_data_type(self):
        make_cache_entry(data_type=WeatherDataType.HOURLY)
        result = get_cached_weather(LAT, LON, WeatherDataType.CURRENT)
        self.assertIsNone(result)

    def test_returns_none_for_different_coordinates(self):
        make_cache_entry(lat=Decimal('0.0'), lon=Decimal('0.0'))
        result = get_cached_weather(LAT, LON, WeatherDataType.CURRENT)
        self.assertIsNone(result)


class SaveWeatherCacheTest(TestCase):
    def test_creates_db_record(self):
        self.assertEqual(WeatherCache.objects.count(), 0)
        save_weather_cache(LAT, LON, WeatherDataType.CURRENT, WEATHER_DATA)
        self.assertEqual(WeatherCache.objects.count(), 1)

    def test_returns_saved_instance_with_correct_fields(self):
        result = save_weather_cache(LAT, LON, WeatherDataType.CURRENT, WEATHER_DATA)
        self.assertIsInstance(result, WeatherCache)
        self.assertIsNotNone(result.pk)
        self.assertEqual(result.lat, LAT)
        self.assertEqual(result.lon, LON)
        self.assertEqual(result.data_type, WeatherDataType.CURRENT)
        self.assertEqual(result.weather_data, WEATHER_DATA)

    def test_raises_integrity_error_for_null_coords(self):
        with self.assertRaises(IntegrityError):
            save_weather_cache(None, None, WeatherDataType.CURRENT, WEATHER_DATA)

    def test_updates_existing_record_on_duplicate_coords(self):
        first = save_weather_cache(LAT, LON, WeatherDataType.CURRENT, WEATHER_DATA)
        new_data = {'current': {'temp': 99.9}}
        result = save_weather_cache(LAT, LON, WeatherDataType.CURRENT, new_data)
        self.assertEqual(WeatherCache.objects.count(), 1)
        self.assertEqual(result.pk, first.pk)
        self.assertEqual(result.weather_data, new_data)

    def test_updates_fetched_at_on_upsert(self):
        old_entry = make_cache_entry(fetched_at=now() - timedelta(minutes=30))
        result = save_weather_cache(LAT, LON, WeatherDataType.CURRENT, WEATHER_DATA)
        self.assertGreater(result.fetched_at, old_entry.fetched_at)

    def test_duplicate_coord_type_raises_integrity_error(self):
        WeatherCache.objects.create(lat=LAT, lon=LON, data_type=WeatherDataType.CURRENT, weather_data=WEATHER_DATA)
        with self.assertRaises(IntegrityError):
            WeatherCache.objects.create(lat=LAT, lon=LON, data_type=WeatherDataType.CURRENT, weather_data=WEATHER_DATA)


@override_settings(WEATHER_CACHE_TTL_MINUTES=60)
@patch('core.weather.services.cache.fetch_weather_from_api')
class GetWeatherTest(TestCase):
    def test_returns_cached_entry_without_calling_api(self, mock_fetch):
        entry = make_cache_entry()
        result = get_weather(LAT, LON, WeatherDataType.CURRENT)
        mock_fetch.assert_not_called()
        self.assertEqual(result.pk, entry.pk)
        self.assertEqual(WeatherCache.objects.count(), 1)

    def test_fetches_from_api_and_saves_when_no_cache(self, mock_fetch):
        mock_fetch.return_value = WEATHER_DATA
        result = get_weather(LAT, LON, WeatherDataType.CURRENT)
        mock_fetch.assert_called_once_with(LAT, LON, WeatherDataType.CURRENT)
        self.assertIsInstance(result, WeatherCache)
        self.assertEqual(result.weather_data, WEATHER_DATA)
        self.assertEqual(WeatherCache.objects.count(), 1)

    def test_fetches_from_api_when_cache_expired(self, mock_fetch):
        make_cache_entry(fetched_at=now() - timedelta(minutes=61))
        mock_fetch.return_value = WEATHER_DATA
        result = get_weather(LAT, LON, WeatherDataType.CURRENT)
        mock_fetch.assert_called_once()
        self.assertEqual(WeatherCache.objects.count(), 1)
        self.assertIsInstance(result, WeatherCache)
        self.assertEqual(result.weather_data, WEATHER_DATA)

    def test_propagates_api_error_without_saving(self, mock_fetch):
        mock_fetch.side_effect = WeatherAPIError('API down')
        with self.assertRaises(WeatherAPIError):
            get_weather(LAT, LON, WeatherDataType.CURRENT)
        self.assertEqual(WeatherCache.objects.count(), 0)
