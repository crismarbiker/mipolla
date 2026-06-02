"""
Generates random match results + random predictions for all users.
Usage:
  python manage.py set_test_results          # mark first 10 matches as played
  python manage.py set_test_results --n 20   # mark first 20
  python manage.py set_test_results --all    # mark all matches
  python manage.py set_test_results --reset  # undo: mark all matches as unplayed
"""
import random
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from polla.models import Partido, Pronostico, SeleccionJugador, GolPartido, Jugador, PerfilUsuario, Pais


class Command(BaseCommand):
    help = 'Generate random results + predictions for testing'

    def add_arguments(self, parser):
        parser.add_argument('--n', type=int, default=10, help='Number of matches to mark as played')
        parser.add_argument('--all', action='store_true', help='Mark all matches as played')
        parser.add_argument('--reset', action='store_true', help='Reset all results')

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
            self.stdout.write(self.style.WARNING('No hay usuarios no-admin. Crea usuarios primero.'))
            return

        # Ensure every user has player selections
        all_players = list(Jugador.objects.all())
        for user in users:
            if not user.jugadores_seleccionados.exists():
                selected = random.sample(all_players, min(5, len(all_players)))
                for j in selected:
                    SeleccionJugador.objects.get_or_create(usuario=user, jugador=j)
                self.stdout.write(f'  → {user.get_full_name()}: {len(selected)} jugadores asignados')

        # Ensure every user has a champion prediction
        paises = list(Pais.objects.all())
        for user in users:
            perfil, _ = PerfilUsuario.objects.get_or_create(usuario=user)
            if not perfil.campeon:
                perfil.campeon = random.choice(paises)
                perfil.save()

        processed = 0
        for partido in partidos:
            # Random result (0-4 goals each team, weighted towards low scores)
            g_local = random.choices([0,1,2,3,4], weights=[20,35,25,15,5])[0]
            g_visit = random.choices([0,1,2,3,4], weights=[20,35,25,15,5])[0]

            partido.goles_local = g_local
            partido.goles_visitante = g_visit
            partido.jugado = True
            partido.save()

            # Random goalscorers from both teams
            local_players = list(Jugador.objects.filter(pais=partido.pais_local))
            visit_players = list(Jugador.objects.filter(pais=partido.pais_visitante))

            for team_players, goals in [(local_players, g_local), (visit_players, g_visit)]:
                if goals > 0 and team_players:
                    scorers = random.sample(team_players, min(goals, len(team_players)))
                    for scorer in scorers:
                        GolPartido.objects.get_or_create(
                            jugador=scorer, partido=partido,
                            defaults={'cantidad': 1}
                        )

            # Recalculate goleador bonus for all affected players
            for gol in partido.goles.all():
                gol.recalcular_bonus_jugador()

            # Create random prediction for each user
            for user in users:
                # 40% chance of exact, 40% correct winner, 20% wrong
                roll = random.random()
                if roll < 0.35:
                    # Exact
                    gl, gv = g_local, g_visit
                elif roll < 0.70:
                    # Correct winner but wrong score
                    if g_local > g_visit:
                        gl = random.randint(1, 3)
                        gv = random.randint(0, gl - 1)
                    elif g_local < g_visit:
                        gv = random.randint(1, 3)
                        gl = random.randint(0, gv - 1)
                    else:
                        gl = gv = random.randint(0, 2)
                else:
                    # Wrong
                    if g_local >= g_visit:
                        gl = random.randint(0, 1)
                        gv = random.randint(gl + 1, gl + 2)
                    else:
                        gv = random.randint(0, 1)
                        gl = random.randint(gv + 1, gv + 2)

                pron, _ = Pronostico.objects.update_or_create(
                    usuario=user, partido=partido,
                    defaults={'goles_local': gl, 'goles_visitante': gv, 'predice_penales': False}
                )
                pron.puntos = pron.calcular_puntos()
                pron.save()

            processed += 1

        # Update champion points
        campeon_real = Pais.objects.filter(es_campeon=True).first()
        if campeon_real:
            for perfil in PerfilUsuario.objects.filter(campeon=campeon_real):
                perfil.puntos_campeon = 15
                perfil.save()

        self.stdout.write(self.style.SUCCESS(
            f'\n✓ {processed} partidos con resultados aleatorios\n'
            f'  {len(users)} usuarios con pronósticos\n'
            f'  Visita /MiPolla/ranking/ para ver la tabla'
        ))
