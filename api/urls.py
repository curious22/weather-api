from django.urls import path

from api.weather.views import WeatherForecastView

urlpatterns = [
    path('weather-forecasts/', WeatherForecastView.as_view(), name='weather-forecasts'),
]
