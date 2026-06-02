"""
Sets fictitious match dates for testing the lockout mechanism.
Each unplayed match gets a start time 1 hour after the previous,
beginning from now + offset_minutes.

Usage:
  python manage.py set_test_dates             # starts 5 min from now, 1h apart
  python manage.py set_test_dates --offset 0  # start immediately
  python manage.py set_test_dates --interval 30  # 30 min apart
  python manage.py set_test_dates --reset     # clear all dates
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from polla.models import Partido


class Command(BaseCommand):
    help = 'Set test dates for matches (for testing lockout behavior)'

    def add_arguments(self, parser):
        parser.add_argument('--offset', type=int, default=5,
                            help='Minutes from now for the FIRST match (default: 5)')
        parser.add_argument('--interval', type=int, default=60,
                            help='Minutes between matches (default: 60)')
        parser.add_argument('--reset', action='store_true',
                            help='Remove all match dates (set to NULL)')

    def handle(self, *args, **options):
        partidos = Partido.objects.filter(jugado=False).order_by('id')

        if options['reset']:
            partidos.update(fecha=None)
            self.stdout.write(self.style.SUCCESS(f'✓ Fechas eliminadas de {partidos.count()} partidos'))
            return

        offset = options['offset']
        interval = options['interval']
        base = timezone.now() + timedelta(minutes=offset)

        updated = 0
        for i, partido in enumerate(partidos):
            partido.fecha = base + timedelta(minutes=i * interval)
            partido.save(update_fields=['fecha'])
            updated += 1

        primer = base
        ultimo = base + timedelta(minutes=(updated - 1) * interval)

        self.stdout.write(self.style.SUCCESS(
            f'\n✓ {updated} partidos actualizados con fechas de prueba\n'
            f'  Primer partido: {primer.strftime("%d/%m/%Y %H:%M")} (en {offset} min)\n'
            f'  Último partido: {ultimo.strftime("%d/%m/%Y %H:%M")}\n'
            f'  Intervalo: {interval} min entre partidos\n\n'
            f'Para restaurar: python manage.py set_test_dates --reset'
        ))
