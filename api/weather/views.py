from rest_framework.response import Response
from rest_framework.views import APIView

from core.weather.services.cache import get_weather

from . import serializers


class WeatherForecastView(APIView):
    def get(self, request):
        serializer = serializers.WeatherForecastQuerySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        data = get_weather(**serializer.validated_data)
        return Response(serializers.WeatherForecastSerializer(instance=data).data)
