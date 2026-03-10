from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler

from core.weather.exceptions import (
    WeatherAPIAuthError,
    WeatherAPIError,
    WeatherAPIRateLimitError,
    WeatherAPIServerError,
)

_STATUS_MAP = {
    # ORDER MATTERS: subclasses must precede base WeatherAPIError,
    # because we use isinstance() which matches parent classes too.
    WeatherAPIAuthError: status.HTTP_502_BAD_GATEWAY,
    WeatherAPIRateLimitError: status.HTTP_503_SERVICE_UNAVAILABLE,
    WeatherAPIServerError: status.HTTP_502_BAD_GATEWAY,
    WeatherAPIError: status.HTTP_502_BAD_GATEWAY,
}


def weather_exception_handler(exc, context):
    for exc_class, status_code in _STATUS_MAP.items():
        if isinstance(exc, exc_class):
            return Response(
                {'detail': 'Weather service is temporarily unavailable. Please try again later.'},
                status=status_code,
            )
    return exception_handler(exc, context)
