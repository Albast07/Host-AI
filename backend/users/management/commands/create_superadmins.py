from django.core.management.base import BaseCommand
from users.models import CustomUser


class Command(BaseCommand):
    help = 'Crear superusuarios ItaloAdmin y DanielAdmin'

    def handle(self, *args, **kwargs):
        # Crear ItaloAdmin
        if not CustomUser.objects.filter(username='ItaloAdmin').exists():
            CustomUser.objects.create_superuser(
                username='ItaloAdmin',
                email='italo.admin2807@gmail.com',
                password='Italo2807Admin',
                role='teacher',
                first_name='Italo',
                last_name='Admin'
            )
            self.stdout.write(self.style.SUCCESS('Superusuario ItaloAdmin creado exitosamente'))
        else:
            self.stdout.write(self.style.WARNING('ItaloAdmin ya existe'))

        # Crear DanielAdmin
        if not CustomUser.objects.filter(username='DanielAdmin').exists():
            CustomUser.objects.create_superuser(
                username='DanielAdmin',
                email='daniel.admin1507@gmail.com',
                password='Daniel1507Admin',
                role='teacher',
                first_name='Daniel',
                last_name='Admin'
            )
            self.stdout.write(self.style.SUCCESS('Superusuario DanielAdmin creado exitosamente'))
        else:
            self.stdout.write(self.style.WARNING('DanielAdmin ya existe'))

        self.stdout.write(self.style.SUCCESS('Proceso completado'))
