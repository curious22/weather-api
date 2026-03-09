class WeatherAPIError(Exception):
    pass


class WeatherAPIAuthError(WeatherAPIError):
    """401 Unauthorized — invalid or missing API key."""

    pass


class WeatherAPIRateLimitError(WeatherAPIError):
    """429 Too Many Requests — rate limit exceeded."""

    pass


class WeatherAPIServerError(WeatherAPIError):
    """5xx — OWM server-side failure."""

    pass
