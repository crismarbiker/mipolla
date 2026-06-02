"""
Full production reset:
1. Deletes all non-admin users (and their predictions)
2. Clears all match results and predictions
3. Resets goleador points and champion selection
4. Sets match dates to FIFA 2026 official schedule (UTC-4 La Paz)
5. Sets cuota to 100 Bs

Usage:
  python manage.py reset_produccion
  python manage.py reset_produccion --confirm
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.db import connection
from django.utils import timezone
from datetime import datetime
import zoneinfo

BOLIVIA = zoneinfo.ZoneInfo('America/La_Paz')


def dt(fecha_str):
    """Parse 'DD/MM HH:MM' → aware datetime in La Paz timezone."""
    d = datetime.strptime(f"2026/{fecha_str}", "%Y/%d/%m %H:%M")
    return d.replace(tzinfo=BOLIVIA)


# FIFA 2026 Official Group Stage Schedule (La Paz time, UTC-4)
# Source: FIFA official match schedule
# All times in GMT-4 (La Paz, Bolivia)
FIFA_SCHEDULE = [
    # ── GRUPO A ──
    # Mexico, Sudafrica, Corea del Sur, Republica Checa
    ('Mexico',          'Sudafrica',       '11/06 15:00'),
    ('Corea del Sur',   'Republica Checa', '12/06 12:00'),
    ('Mexico',          'Republica Checa', '16/06 15:00'),
    ('Corea del Sur',   'Sudafrica',       '16/06 12:00'),
    ('Mexico',          'Corea del Sur',   '22/06 15:00'),
    ('Republica Checa', 'Sudafrica',       '22/06 15:00'),
    # ── GRUPO B ──
    # Canada, Bosnia Herzegovina, Qatar, Suiza
    ('Canada',          'Qatar',               '12/06 18:00'),
    ('Bosnia Herzegovina','Suiza',             '13/06 12:00'),
    ('Canada',          'Suiza',               '17/06 18:00'),
    ('Bosnia Herzegovina','Qatar',             '17/06 15:00'),
    ('Canada',          'Bosnia Herzegovina',  '23/06 18:00'),
    ('Suiza',           'Qatar',               '23/06 18:00'),
    # ── GRUPO C ──
    # Brasil, Marruecos, Haiti, Escocia
    ('Brasil',    'Marruecos', '13/06 18:00'),
    ('Haiti',     'Escocia',   '13/06 15:00'),
    ('Brasil',    'Escocia',   '18/06 18:00'),
    ('Haiti',     'Marruecos', '18/06 15:00'),
    ('Brasil',    'Haiti',     '24/06 18:00'),
    ('Escocia',   'Marruecos', '24/06 18:00'),
    # ── GRUPO D ──
    # Estados Unidos, Paraguay, Australia, Turquia
    ('Estados Unidos', 'Paraguay',   '14/06 17:00'),
    ('Australia',      'Turquia',    '14/06 14:00'),
    ('Estados Unidos', 'Turquia',    '19/06 17:00'),
    ('Australia',      'Paraguay',   '19/06 14:00'),
    ('Estados Unidos', 'Australia',  '25/06 17:00'),
    ('Turquia',        'Paraguay',   '25/06 17:00'),
    # ── GRUPO E ──
    # Alemania, Curazao, Costa de Marfil, Ecuador
    ('Alemania',      'Curazao',       '14/06 20:00'),
    ('Costa de Marfil','Ecuador',      '15/06 12:00'),
    ('Alemania',      'Ecuador',       '19/06 20:00'),
    ('Costa de Marfil','Curazao',      '20/06 12:00'),
    ('Alemania',      'Costa de Marfil','25/06 20:00'),
    ('Ecuador',       'Curazao',       '25/06 20:00'),
    # ── GRUPO F ──
    # Holanda, Japon, Suecia, Tunez
    ('Holanda',  'Japon',  '15/06 17:00'),
    ('Suecia',   'Tunez',  '15/06 20:00'),
    ('Holanda',  'Tunez',  '20/06 17:00'),
    ('Suecia',   'Japon',  '20/06 20:00'),
    ('Holanda',  'Suecia', '26/06 20:00'),
    ('Japon',    'Tunez',  '26/06 20:00'),
    # ── GRUPO G ──
    # Belgica, Egipto, Iran, Nueva Zelanda
    ('Belgica',       'Egipto',        '15/06 15:00'),
    ('Iran',          'Nueva Zelanda', '16/06 12:00'),
    ('Belgica',       'Nueva Zelanda', '20/06 15:00'),
    ('Iran',          'Egipto',        '21/06 12:00'),
    ('Belgica',       'Iran',          '26/06 17:00'),
    ('Nueva Zelanda', 'Egipto',        '26/06 17:00'),
    # ── GRUPO H ──
    # Espana, Cabo Verde, Arabia Saudita, Uruguay
    ('Espana',       'Cabo Verde',    '16/06 20:00'),
    ('Arabia Saudita','Uruguay',      '16/06 17:00'),
    ('Espana',       'Uruguay',       '21/06 20:00'),
    ('Arabia Saudita','Cabo Verde',   '21/06 17:00'),
    ('Espana',       'Arabia Saudita','27/06 20:00'),
    ('Uruguay',      'Cabo Verde',    '27/06 20:00'),
    # ── GRUPO I ──
    # Francia, Senegal, Irak, Noruega
    ('Francia',  'Senegal', '17/06 12:00'),
    ('Irak',     'Noruega', '17/06 20:00'),
    ('Francia',  'Noruega', '22/06 12:00'),
    ('Irak',     'Senegal', '22/06 20:00'),
    ('Francia',  'Irak',    '28/06 20:00'),
    ('Noruega',  'Senegal', '28/06 20:00'),
    # ── GRUPO J ──
    # Argentina, Argelia, Austria, Jordania
    ('Argentina', 'Argelia', '18/06 20:00'),
    ('Austria',   'Jordania','18/06 12:00'),
    ('Argentina', 'Jordania','23/06 20:00'),
    ('Austria',   'Argelia', '23/06 12:00'),
    ('Argentina', 'Austria', '28/06 17:00'),
    ('Jordania',  'Argelia', '28/06 17:00'),
    # ── GRUPO K ──
    # Portugal, Congo DR, Uzbekistan, Colombia
    ('Portugal',  'Congo DR',   '19/06 12:00'),
    ('Uzbekistan','Colombia',   '19/06 15:00'),
    ('Portugal',  'Colombia',   '24/06 12:00'),
    ('Uzbekistan','Congo DR',   '24/06 15:00'),
    ('Portugal',  'Uzbekistan', '29/06 20:00'),
    ('Colombia',  'Congo DR',   '29/06 20:00'),
    # ── GRUPO L ──
    # Inglaterra, Croacia, Ghana, Panama
    ('Inglaterra', 'Croacia', '20/06 18:00'),
    ('Ghana',      'Panama',  '21/06 15:00'),
    ('Inglaterra', 'Panama',  '25/06 12:00'),
    ('Ghana',      'Croacia', '25/06 15:00'),
    ('Inglaterra', 'Ghana',   '29/06 17:00'),
    ('Croacia',    'Panama',  '29/06 17:00'),
]


class Command(BaseCommand):
    help = 'Full production reset: delete test data, load official FIFA 2026 schedule'

    def add_arguments(self, parser):
        parser.add_argument('--confirm', action='store_true',
                            help='Required to actually execute (safety check)')

    def handle(self, *args, **options):
        if not options['confirm']:
            self.stdout.write(self.style.WARNING(
                '\n⚠️  ESTE COMANDO BORRA DATOS DE PRODUCCIÓN\n'
                'Ejecuta con --confirm para proceder:\n'
                '  python manage.py reset_produccion --confirm\n'
            ))
            return

        from polla.models import (Partido, Pronostico, GolPartido, SeleccionJugador,
                                   PerfilUsuario, Pais, TorneoConfig)

        # 1. Delete non-admin users
        non_admins = User.objects.filter(is_staff=False)
        count_users = non_admins.count()
        non_admins.delete()
        self.stdout.write(f'✓ Eliminados {count_users} usuarios no-admin')

        # 2. Clear all predictions and results
        Pronostico.objects.all().delete()
        GolPartido.objects.all().delete()
        Partido.objects.update(
            jugado=False, goles_local=None, goles_visitante=None,
            hubo_penales=False, penales_local=None, penales_visitante=None
        )
        SeleccionJugador.objects.all().delete()
        PerfilUsuario.objects.update(campeon=None, puntos_campeon=0)
        Pais.objects.update(es_campeon=False)
        self.stdout.write('✓ Pronósticos, goles y resultados eliminados')

        # 3. Set cuota to 100 Bs
        torneo = TorneoConfig.get()
        torneo.cuota = 100
        torneo.whatsapp_pago = '59170512621'
        torneo.save()
        self.stdout.write('✓ Cuota: Bs. 100 | WhatsApp pago: 59170512621')

        # 4. Load FIFA 2026 official schedule
        from polla.models import Fase
        from django.db.models import Q
        fase_grupos = Fase.objects.get(id_fase=1)
        updated = 0
        not_found = 0

        for local_name, visitante_name, fecha_str in FIFA_SCHEDULE:
            try:
                local = Pais.objects.get(nombre=local_name)
                visitante = Pais.objects.get(nombre=visitante_name)
            except Pais.DoesNotExist:
                self.stdout.write(self.style.WARNING(f'  País no encontrado: {local_name} o {visitante_name}'))
                not_found += 1
                continue

            fecha = dt(fecha_str)
            cnt = Partido.objects.filter(fase=fase_grupos).filter(
                (Q(pais_local=local) & Q(pais_visitante=visitante)) |
                (Q(pais_local=visitante) & Q(pais_visitante=local))
            ).update(fecha=fecha)

            if cnt == 0:
                not_found += 1
            else:
                updated += cnt

        self.stdout.write(f'✓ Fechas actualizadas: {updated} partidos')
        if not_found:
            self.stdout.write(self.style.WARNING(f'  ⚠ {not_found} partidos no encontrados (verificar nombres)'))

        # 5. Clear knockout round matches (only keep group stage)
        Partido.objects.filter(fase__id_fase__gt=1).delete()
        self.stdout.write('✓ Partidos de eliminatoria eliminados (se generarán cuando corresponda)')

        self.stdout.write(self.style.SUCCESS(
            '\n✅ Reset completado. Listo para producción.\n'
            f'Partidos de grupos: {Partido.objects.filter(fase__id_fase=1).count()}\n'
            'Próximos pasos:\n'
            '  1. Subir QR de pago: Django Admin → Configuración del torneo → QR de pago\n'
            '  2. Verificar fechas en: Django Admin → Partidos\n'
            '  3. Landing page: https://www.elcarguero.com/MiPolla/unirse/\n'
        ))
