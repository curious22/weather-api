from rest_framework.mixins import ListModelMixin
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from core.weather.services.cache import get_weather

from . import serializers


class WeatherForecastView(ListModelMixin, GenericViewSet):
    serializer_class = serializers.WeatherForecastSerializer

    def list(self, request, *args, **kwargs):
        serializer = serializers.WeatherForecastQuerySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        data = get_weather(**serializer.validated_data)
        return Response(serializers.WeatherForecastSerializer(instance=data).data)
