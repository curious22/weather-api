from django.db import models

from .enums import WeatherDataType


class WeatherCache(models.Model):
    lat = models.DecimalField(max_digits=9, decimal_places=6)
    lon = models.DecimalField(max_digits=9, decimal_places=6)
    data_type = models.CharField(choices=WeatherDataType, max_length=10)
    fetched_at = models.DateTimeField(auto_now_add=True)
    weather_data = models.JSONField()

    class Meta:
        db_table = 'weather_cache'
        indexes = [models.Index(fields=('lat', 'lon', 'data_type', 'fetched_at'))]
