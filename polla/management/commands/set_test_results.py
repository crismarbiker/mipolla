"""
Generates random match results + predictions for all users.
Usage:
  python manage.py set_test_results          # 10 matches
  python manage.py set_test_results --n 20   # 20 matches
  python manage.py set_test_results --all    # all matches
  python manage.py set_test_results --reset  # undo results
"""
import random
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.db import connection
from django.db.models import Sum
from polla.models import (Partido, Pronostico, SeleccionJugador,
                           GolPartido, Jugador, PerfilUsuario, Pais)


class Command(BaseCommand):
    help = 'Generate random results + predictions (bypasses tournament lock)'

    def add_arguments(self, parser):
        parser.add_argument('--n', type=int, default=10)
        parser.add_argument('--all', action='store_true')
        parser.add_argument('--reset', action='store_true')

    def handle(self, *args, **options):
        if options['reset']:
            Partido.objects.update(jugado=False, goles_local=None, goles_visitante=None)
            GolPartido.objects.all().delete()
            Pronostico.objects.update(puntos=0)
            self.stdout.write(self.style.SUCCESS('Resultados reseteados.'))
            return

        partidos = Partido.objects.filter(jugado=False).order_by('fecha')
        if not options['all']:
            partidos = partidos[:options['n']]
        partidos = list(partidos)

        users = list(User.objects.filter(is_active=True, is_staff=False))
        if not users:
            self.stdout.write(self.style.WARNING('No hay usuarios. Crea usuarios primero.'))
            return

        all_players = list(Jugador.objects.all())
        paises = list(Pais.objects.all())

        # Assign players + champion using raw SQL (bypasses tournament lock in save())
        for user in users:
            if not user.jugadores_seleccionados.exists():
                selected = random.sample(all_players, min(5, len(all_players)))
                with connection.cursor() as cur:
                    for j in selected:
                        cur.execute(
                            'INSERT INTO polla_seleccionjugador (usuario_id,jugador_id,puntos_acumulados) '
                            'VALUES (%s,%s,0) ON CONFLICT DO NOTHING', [user.id, j.id])
                self.stdout.write(f'  → {user.get_full_name()}: 5 jugadores asignados')
            perfil, _ = PerfilUsuario.objects.get_or_create(usuario=user)
            if not perfil.campeon:
                perfil.campeon = random.choice(paises)
                perfil.save()

        for partido in partidos:
            gl = random.choices([0,1,2,3,4], weights=[20,35,25,15,5])[0]
            gv = random.choices([0,1,2,3,4], weights=[20,35,25,15,5])[0]
            partido.goles_local = gl; partido.goles_visitante = gv
            partido.jugado = True; partido.save()

            for team_pls, goals in [
                (list(Jugador.objects.filter(pais=partido.pais_local)), gl),
                (list(Jugador.objects.filter(pais=partido.pais_visitante)), gv),
            ]:
                if goals > 0 and team_pls:
                    for scorer in random.sample(team_pls, min(goals, len(team_pls))):
                        GolPartido.objects.get_or_create(jugador=scorer, partido=partido, defaults={'cantidad': 1})
            for gol in partido.goles.all():
                gol.recalcular_bonus_jugador()

            for user in users:
                roll = random.random()
                if roll < 0.35:
                    pgl, pgv = gl, gv
                elif roll < 0.70:
                    if gl > gv: pgl = random.randint(1,3); pgv = random.randint(0, pgl-1)
                    elif gl < gv: pgv = random.randint(1,3); pgl = random.randint(0, pgv-1)
                    else: pgl = pgv = random.randint(0, 2)
                else:
                    if gl >= gv: pgl = random.randint(0,1); pgv = pgl + random.randint(1,2)
                    else: pgv = random.randint(0,1); pgl = pgv + random.randint(1,2)

                with connection.cursor() as cur:
                    cur.execute(
                        'INSERT INTO polla_pronostico '
                        '(usuario_id,partido_id,goles_local,goles_visitante,predice_penales,puntos,creado,actualizado) '
                        'VALUES (%s,%s,%s,%s,false,0,NOW(),NOW()) '
                        'ON CONFLICT (usuario_id,partido_id) DO UPDATE '
                        'SET goles_local=%s,goles_visitante=%s,actualizado=NOW()',
                        [user.id, partido.id, pgl, pgv, pgl, pgv])
                pron = Pronostico.objects.get(usuario=user, partido=partido)
                Pronostico.objects.filter(pk=pron.pk).update(puntos=pron.calcular_puntos())

        self.stdout.write(self.style.SUCCESS(
            f'\n✓ {len(partidos)} partidos · {len(users)} usuarios'
        ))
        for u in sorted(users, key=lambda x: -(
            (x.pronosticos.filter(partido__jugado=True).aggregate(t=Sum('puntos'))['t'] or 0) +
            (x.jugadores_seleccionados.aggregate(t=Sum('puntos_acumulados'))['t'] or 0)
        )):
            pts = (u.pronosticos.filter(partido__jugado=True).aggregate(t=Sum('puntos'))['t'] or 0)
            pts_g = (u.jugadores_seleccionados.aggregate(t=Sum('puntos_acumulados'))['t'] or 0)
            self.stdout.write(f'  {u.get_full_name():25} {pts + pts_g} pts')
