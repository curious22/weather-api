from rest_framework import serializers

from core.weather import enums, models


class WeatherForecastQuerySerializer(serializers.Serializer):
    lat = serializers.DecimalField(max_digits=9, decimal_places=6)
    lon = serializers.DecimalField(max_digits=9, decimal_places=6)
    data_type = serializers.ChoiceField(choices=enums.WeatherDataType.choices)

    def validate_lat(self, value):
        if not (-90 <= value <= 90):
            raise serializers.ValidationError('Latitude must be between -90 and 90.')
        return value

    def validate_lon(self, value):
        if not (-180 <= value <= 180):
            raise serializers.ValidationError('Longitude must be between -180 and 180.')
        return value


class WeatherForecastSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.WeatherCache
        fields = ('id', 'lat', 'lon', 'data_type', 'fetched_at', 'weather_data')
