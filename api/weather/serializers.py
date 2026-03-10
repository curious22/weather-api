from rest_framework import serializers

from core.weather import enums, models


class WeatherForecastQuerySerializer(serializers.Serializer):
    lat = serializers.DecimalField(max_digits=9, decimal_places=6, min_value=-90, max_value=90)
    lon = serializers.DecimalField(max_digits=9, decimal_places=6, min_value=-180, max_value=180)
    data_type = serializers.ChoiceField(choices=enums.WeatherDataType.choices)


class WeatherForecastSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.WeatherCache
        fields = ('id', 'lat', 'lon', 'data_type', 'fetched_at', 'weather_data')
