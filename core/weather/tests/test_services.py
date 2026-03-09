from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings
from requests import exceptions as req_exc

from core.weather.enums import WeatherDataType
from core.weather.exceptions import (
    WeatherAPIAuthError,
    WeatherAPIError,
    WeatherAPIRateLimitError,
    WeatherAPIServerError,
)
from core.weather.services.owm_client import fetch_weather_from_api

LAT, LON = 47.8387, 35.1383


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
        self.assertIn('https://api.openweathermap.org/data/3.0/onecall', call_args.args[0])
