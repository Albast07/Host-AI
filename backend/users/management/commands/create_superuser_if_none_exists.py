import os
from django.core.management.base import BaseCommand
from users.models import CustomUser


class Command(BaseCommand):
    help = 'Crea un superusuario automáticamente si no existe'

    def handle(self, *args, **options):
        username = os.getenv('DJANGO_SUPERUSER_USERNAME', 'admin')
        email = os.getenv('DJANGO_SUPERUSER_EMAIL', 'admin@example.com')
        password = os.getenv('DJANGO_SUPERUSER_PASSWORD', 'admin123')

        if not CustomUser.objects.filter(username=username).exists():
            CustomUser.objects.create_superuser(
                username=username,
                email=email,
                password=password,
                role='teacher'  # Como superusuario, le damos rol de profesor
            )
            self.stdout.write(self.style.SUCCESS(f'Superusuario "{username}" creado exitosamente'))
        else:
            self.stdout.write(self.style.WARNING(f'El superusuario "{username}" ya existe'))
