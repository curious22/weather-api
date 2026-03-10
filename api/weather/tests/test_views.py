from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from core.weather.enums import WeatherDataType
from core.weather.exceptions import (
    WeatherAPIAuthError,
    WeatherAPIError,
    WeatherAPIRateLimitError,
    WeatherAPIServerError,
)
from core.weather.models import WeatherCache

User = get_user_model()

URL = '/api/v1/weather-forecasts/'
LAT, LON = '47.838700', '35.138300'
WEATHER_DATA = {'current': {'temp': 20.5}}
SERVICE_UNAVAILABLE_MSG = 'Weather service is temporarily unavailable. Please try again later.'


def make_cache_entry(lat=Decimal(LAT), lon=Decimal(LON), data_type=WeatherDataType.CURRENT, weather_data=None):
    return WeatherCache.objects.create(
        lat=lat,
        lon=lon,
        data_type=data_type,
        weather_data=weather_data or WEATHER_DATA,
    )


class WeatherForecastViewTest(APITestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='testuser', password='pass')
        cls.token = Token.objects.create(user=cls.user)

    def setUp(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')

    # -------------------------------------------------------------------------
    # Authentication
    # -------------------------------------------------------------------------

    def test_unauthenticated_request_returns_401(self):
        self.client.credentials()
        response = self.client.get(URL, {'lat': LAT, 'lon': LON, 'data_type': 'current'})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # -------------------------------------------------------------------------
    # Query param validation
    # -------------------------------------------------------------------------

    def test_missing_lat_returns_400(self):
        response = self.client.get(URL, {'lon': LON, 'data_type': 'current'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('This field is required.', str(response.data['lat']))

    def test_missing_lon_returns_400(self):
        response = self.client.get(URL, {'lat': LAT, 'data_type': 'current'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('This field is required.', str(response.data['lon']))

    def test_missing_data_type_returns_400(self):
        response = self.client.get(URL, {'lat': LAT, 'lon': LON})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('This field is required.', str(response.data['data_type']))

    def test_lat_above_90_returns_400(self):
        response = self.client.get(URL, {'lat': '91', 'lon': LON, 'data_type': 'current'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Latitude must be between -90 and 90.', str(response.data['lat']))

    def test_lat_below_minus_90_returns_400(self):
        response = self.client.get(URL, {'lat': '-91', 'lon': LON, 'data_type': 'current'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Latitude must be between -90 and 90.', str(response.data['lat']))

    def test_lon_above_180_returns_400(self):
        response = self.client.get(URL, {'lat': LAT, 'lon': '181', 'data_type': 'current'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Longitude must be between -180 and 180.', str(response.data['lon']))

    def test_lon_below_minus_180_returns_400(self):
        response = self.client.get(URL, {'lat': LAT, 'lon': '-181', 'data_type': 'current'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Longitude must be between -180 and 180.', str(response.data['lon']))

    def test_invalid_data_type_returns_400(self):
        response = self.client.get(URL, {'lat': LAT, 'lon': LON, 'data_type': 'invalid'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('"invalid" is not a valid choice.', str(response.data['data_type']))

    # -------------------------------------------------------------------------
    # Success response format
    # -------------------------------------------------------------------------

    @patch('api.weather.views.get_weather')
    def test_success_returns_200_with_correct_fields(self, mock_get_weather):
        entry = make_cache_entry()
        mock_get_weather.return_value = entry

        response = self.client.get(URL, {'lat': LAT, 'lon': LON, 'data_type': 'current'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data

        self.assertIn('id', data)
        self.assertEqual(data['id'], entry.pk)

        self.assertIn('lat', data)
        self.assertEqual(data['lat'], LAT)

        self.assertIn('lon', data)
        self.assertEqual(data['lon'], LON)

        self.assertIn('data_type', data)
        self.assertEqual(data['data_type'], WeatherDataType.CURRENT)

        self.assertIn('fetched_at', data)
        self.assertIsNotNone(data['fetched_at'])

        self.assertIn('weather_data', data)
        self.assertEqual(data['weather_data'], WEATHER_DATA)

    @patch('api.weather.views.get_weather')
    def test_service_called_with_correct_params(self, mock_get_weather):
        entry = make_cache_entry()
        mock_get_weather.return_value = entry

        self.client.get(URL, {'lat': LAT, 'lon': LON, 'data_type': 'current'})

        mock_get_weather.assert_called_once_with(
            lat=Decimal(LAT),
            lon=Decimal(LON),
            data_type=WeatherDataType.CURRENT,
        )

    # -------------------------------------------------------------------------
    # Service error handling
    # -------------------------------------------------------------------------

    @patch('api.weather.views.get_weather')
    def test_weather_api_auth_error_returns_502(self, mock_get_weather):
        mock_get_weather.side_effect = WeatherAPIAuthError('invalid key')
        response = self.client.get(URL, {'lat': LAT, 'lon': LON, 'data_type': 'current'})
        self.assertEqual(response.status_code, status.HTTP_502_BAD_GATEWAY)
        self.assertEqual(response.data['detail'], SERVICE_UNAVAILABLE_MSG)

    @patch('api.weather.views.get_weather')
    def test_weather_api_rate_limit_error_returns_503(self, mock_get_weather):
        mock_get_weather.side_effect = WeatherAPIRateLimitError('rate limit')
        response = self.client.get(URL, {'lat': LAT, 'lon': LON, 'data_type': 'current'})
        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertEqual(response.data['detail'], SERVICE_UNAVAILABLE_MSG)

    @patch('api.weather.views.get_weather')
    def test_weather_api_server_error_returns_502(self, mock_get_weather):
        mock_get_weather.side_effect = WeatherAPIServerError('server error')
        response = self.client.get(URL, {'lat': LAT, 'lon': LON, 'data_type': 'current'})
        self.assertEqual(response.status_code, status.HTTP_502_BAD_GATEWAY)
        self.assertEqual(response.data['detail'], SERVICE_UNAVAILABLE_MSG)

    @patch('api.weather.views.get_weather')
    def test_weather_api_generic_error_returns_502(self, mock_get_weather):
        mock_get_weather.side_effect = WeatherAPIError('unknown error')
        response = self.client.get(URL, {'lat': LAT, 'lon': LON, 'data_type': 'current'})
        self.assertEqual(response.status_code, status.HTTP_502_BAD_GATEWAY)
        self.assertEqual(response.data['detail'], SERVICE_UNAVAILABLE_MSG)
