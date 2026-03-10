from rest_framework.routers import SimpleRouter

from api.weather.views import WeatherForecastView

router = SimpleRouter()
router.register(r'weather-forecasts', WeatherForecastView, basename='weather-forecasts')

urlpatterns = router.urls
