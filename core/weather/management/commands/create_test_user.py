import secrets
import string

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from rest_framework.authtoken.models import Token

_SEPARATOR = '-' * 48
_PASSWORD_ALPHABET = string.ascii_letters + string.digits + '!@#$%^&*'
_PASSWORD_LENGTH = 16


def _generate_password() -> str:
    return ''.join(secrets.choice(_PASSWORD_ALPHABET) for _ in range(_PASSWORD_LENGTH))


class Command(BaseCommand):
    help = 'Create a test user with a DRF auth token for API testing'

    def add_arguments(self, parser):
        parser.add_argument(
            '--username',
            type=str,
            default=None,
            help='Username for the new user (default: auto-generated)',
        )
        parser.add_argument(
            '--superuser',
            action='store_true',
            default=False,
            help='Create a superuser instead of a regular user',
        )

    def handle(self, *args, **options):
        username = options['username'] or f'user_{secrets.token_hex(4)}'
        password = _generate_password()
        is_superuser = options['superuser']

        if User.objects.filter(username=username).exists():
            raise CommandError(f"User '{username}' already exists.")

        if is_superuser:
            user = User.objects.create_superuser(username=username, password=password, email='')
        else:
            user = User.objects.create_user(username=username, password=password)

        token, _ = Token.objects.get_or_create(user=user)

        user_type = 'Superuser' if is_superuser else 'User'
        curl_example = (
            f'curl -H "Authorization: Token {token.key}" '
            f'"http://localhost:8000/api/v1/weather-forecasts/?lat=50.45&lon=30.52&data_type=current"'
        )

        self.stdout.write(self.style.SUCCESS(_SEPARATOR))
        self.stdout.write(self.style.SUCCESS(f'  {user_type} created successfully'))
        self.stdout.write(self.style.SUCCESS(_SEPARATOR))
        self.stdout.write(f'  {"Username":<10}: {self.style.WARNING(username)}')
        self.stdout.write(f'  {"Password":<10}: {self.style.WARNING(password)}')
        self.stdout.write(f'  {"Token":<10}: {self.style.WARNING(token.key)}')
        self.stdout.write(self.style.SUCCESS(_SEPARATOR))
        self.stdout.write('  curl example:')
        self.stdout.write(f'  {curl_example}')
        self.stdout.write(self.style.SUCCESS(_SEPARATOR))
