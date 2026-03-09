from django.db.models import TextChoices


class WeatherDataType(TextChoices):
    CURRENT = 'current', 'Current'
    MINUTELY = 'minutely', 'Minutely'
    HOURLY = 'hourly', 'Hourly'
    DAILY = 'daily', 'Daily'
