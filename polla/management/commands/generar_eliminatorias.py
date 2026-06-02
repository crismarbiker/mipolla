"""
Auto-generates knockout round matches (R32, R16, QF, SF, 3rd, Final)
based on completed group stage results.

FIFA 2026 World Cup bracket structure:
- 12 groups (A-L) × 4 teams = 48 teams
- Top 2 each group + 8 best 3rd-place = 32 teams in Round of 32
- R32 → R16 → QF → SF → 3rd Place → Final

R32 pairings (FIFA 2026 official bracket):
Slot  | Team 1      | Team 2
1     | Winner A    | Runner-up C
2     | Winner B    | Runner-up F
3     | Winner C    | Runner-up A
4     | Winner D    | Runner-up H
5     | Winner E    | Runner-up D
6     | Winner F    | Runner-up B
7     | Winner G    | Runner-up L
8     | Winner H    | Runner-up G
9     | Winner I    | Runner-up K
10    | Winner J    | Runner-up I
11    | Winner K    | Runner-up J
12    | Winner L    | Runner-up E
13-16 | Best 3rd-place teams fill remaining slots

Usage:
  python manage.py generar_eliminatorias --fase R32   # Generate Round of 32
  python manage.py generar_eliminatorias --fase R16   # After R32 is done
  python manage.py generar_eliminatorias --fase QF    # After R16 is done
  python manage.py generar_eliminatorias --fase SF    # After QF is done
  python manage.py generar_eliminatorias --fase FINAL # After SF is done
  python manage.py generar_eliminatorias --all        # Try to generate all possible
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Sum, Q
from datetime import timedelta
from polla.models import Partido, Fase, Pais, Estadio


# FIFA 2026 R32 bracket: (winner_group, runner_up_group)
# Groups 1-12 = A-L
R32_BRACKET = [
    (1, 3),   # 1A vs 2C
    (2, 6),   # 1B vs 2F
    (3, 1),   # 1C vs 2A
    (4, 8),   # 1D vs 2H
    (5, 4),   # 1E vs 2D
    (6, 2),   # 1F vs 2B
    (7, 12),  # 1G vs 2L
    (8, 7),   # 1H vs 2G
    (9, 11),  # 1I vs 2K
    (10, 9),  # 1J vs 2I
    (11, 10), # 1K vs 2J
    (12, 5),  # 1L vs 2E
    # 4 matches for best 3rd-place teams — filled dynamically
]

LETRA = {1:'A',2:'B',3:'C',4:'D',5:'E',6:'F',7:'G',8:'H',9:'I',10:'J',11:'K',12:'L'}

# R16, QF, SF bracket (which R32 match winners play each other)
R16_BRACKET = [(1,2),(3,4),(5,6),(7,8),(9,10),(11,12),(13,14),(15,16)]
QF_BRACKET  = [(1,2),(3,4),(5,6),(7,8)]
SF_BRACKET  = [(1,2),(3,4)]


class Command(BaseCommand):
    help = 'Auto-generate knockout round matches from group results'

    def add_arguments(self, parser):
        parser.add_argument('--fase', type=str, default='R32',
                            choices=['R32', 'R16', 'QF', 'SF', 'FINAL'],
                            help='Which phase to generate')
        parser.add_argument('--all', action='store_true',
                            help='Generate all possible phases')
        parser.add_argument('--dry-run', action='store_true',
                            help='Show what would be created without saving')

    def handle(self, *args, **options):
        if options['all']:
            for fase in ['R32', 'R16', 'QF', 'SF', 'FINAL']:
                self._generar(fase, options['dry_run'])
        else:
            self._generar(options['fase'], options['dry_run'])

    def _calcular_posicion_grupo(self, grupo_num):
        """Returns (winner, runner_up, best_thirds) for a group."""
        partidos = Partido.objects.filter(
            fase__id_fase=1,
            jugado=True
        ).filter(
            Q(pais_local__grupo=grupo_num) | Q(pais_visitante__grupo=grupo_num)
        )
        paises = list(Pais.objects.filter(grupo=grupo_num))
        stats = {}
        for p in paises:
            stats[p.id] = {'pais': p, 'pts': 0, 'gf': 0, 'gc': 0, 'gd': 0, 'pj': 0}

        for partido in partidos:
            lp = stats.get(partido.pais_local_id)
            vp = stats.get(partido.pais_visitante_id)
            if not lp or not vp:
                continue
            gl = partido.goles_local or 0
            gv = partido.goles_visitante or 0
            lp['pj'] += 1; vp['pj'] += 1
            lp['gf'] += gl; lp['gc'] += gv
            vp['gf'] += gv; vp['gc'] += gl

            if gl > gv:
                lp['pts'] += 3
            elif gl == gv:
                lp['pts'] += 1; vp['pts'] += 1
            else:
                vp['pts'] += 3

        for s in stats.values():
            s['gd'] = s['gf'] - s['gc']

        ranked = sorted(stats.values(), key=lambda x: (-x['pts'], -x['gd'], -x['gf']))
        return ranked

    def _generar(self, nombre_fase, dry_run):
        fase_map = {'R32': 2, 'R16': 3, 'QF': 4, 'SF': 5, 'FINAL_AND_3RD': (6,7)}
        fase_id = {'R32': 2, 'R16': 3, 'QF': 4, 'SF': 5, 'FINAL': 7}[nombre_fase]

        fase = Fase.objects.filter(id_fase=fase_id).first()
        if not fase:
            self.stdout.write(self.style.ERROR(f'Fase {nombre_fase} no existe en la base de datos.'))
            return

        if nombre_fase == 'R32':
            self._generar_r32(fase, dry_run)
        elif nombre_fase == 'R16':
            self._generar_fase(fase, 2, R16_BRACKET, 'R32', dry_run)
        elif nombre_fase == 'QF':
            self._generar_fase(fase, 3, QF_BRACKET, 'R16', dry_run)
        elif nombre_fase == 'SF':
            self._generar_fase(fase, 4, SF_BRACKET, 'QF', dry_run)
        elif nombre_fase == 'FINAL':
            self._generar_final(dry_run)

    def _generar_r32(self, fase, dry_run):
        # Check all group matches played
        total_grupos = Partido.objects.filter(fase__id_fase=1).count()
        jugados_grupos = Partido.objects.filter(fase__id_fase=1, jugado=True).count()

        if jugados_grupos < total_grupos:
            pendientes = total_grupos - jugados_grupos
            self.stdout.write(self.style.WARNING(
                f'Faltan {pendientes} partidos de grupos por jugarse. '
                f'({jugados_grupos}/{total_grupos} completados)'
            ))

        # Get standings per group
        grupos = {}
        for g in range(1, 13):
            ranked = self._calcular_posicion_grupo(g)
            grupos[g] = ranked

        # Get best 8 third-place teams
        terceros = []
        for g in range(1, 13):
            ranked = grupos.get(g, [])
            if len(ranked) >= 3 and ranked[2]['pj'] > 0:
                t = ranked[2].copy()
                t['grupo'] = g
                terceros.append(t)

        terceros.sort(key=lambda x: (-x['pts'], -x['gd'], -x['gf']))
        mejores_terceros = terceros[:8]

        # Create R32 matches
        estadio = Estadio.objects.first()
        base_date = timezone.now() + timedelta(days=30)
        created = 0

        self.stdout.write(f'\n=== Generando Round of 32 ===')

        for i, (gw, gr) in enumerate(R32_BRACKET):
            w_list = grupos.get(gw, [])
            r_list = grupos.get(gr, [])
            if not w_list or not r_list:
                continue

            local = w_list[0]['pais']
            visitante = r_list[1]['pais'] if len(r_list) > 1 else r_list[0]['pais']

            msg = f'  Partido {i+1}: 1{LETRA[gw]} ({local.nombre}) vs 2{LETRA[gr]} ({visitante.nombre})'
            self.stdout.write(msg)

            if not dry_run:
                partido, c = Partido.objects.get_or_create(
                    fase=fase,
                    pais_local=local,
                    pais_visitante=visitante,
                    defaults={
                        'estadio': estadio,
                        'fecha': base_date + timedelta(hours=i * 3),
                        'jugado': False,
                    }
                )
                if c:
                    created += 1

        # Create 4 matches for best 3rd-place teams
        for i, t in enumerate(mejores_terceros[:4]):
            opponent_idx = i + 4  # pair with positions 5-8
            if opponent_idx < len(mejores_terceros):
                local = t['pais']
                visitante = mejores_terceros[opponent_idx]['pais']
                g1 = t['grupo']; g2 = mejores_terceros[opponent_idx]['grupo']
                msg = f'  3°: 3{LETRA[g1]} ({local.nombre}) vs 3{LETRA[g2]} ({visitante.nombre})'
                self.stdout.write(msg)
                if not dry_run:
                    partido, c = Partido.objects.get_or_create(
                        fase=fase, pais_local=local, pais_visitante=visitante,
                        defaults={
                            'estadio': estadio,
                            'fecha': base_date + timedelta(hours=(12 + i) * 3),
                            'jugado': False,
                        }
                    )
                    if c:
                        created += 1

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN — ningún partido creado.'))
        else:
            self.stdout.write(self.style.SUCCESS(f'✓ {created} nuevos partidos de R32 creados.'))

    def _generar_fase(self, fase, fase_anterior_id, bracket, nombre_anterior, dry_run):
        partidos_anteriores = list(
            Partido.objects.filter(fase__id_fase=fase_anterior_id, jugado=True).order_by('fecha', 'id')
        )
        pendientes = Partido.objects.filter(fase__id_fase=fase_anterior_id, jugado=False).count()
        if pendientes > 0:
            self.stdout.write(self.style.WARNING(
                f'Faltan {pendientes} partidos de {nombre_anterior} por jugarse.'
            ))

        estadio = Estadio.objects.first()
        base_date = timezone.now() + timedelta(days=60)
        created = 0

        self.stdout.write(f'\n=== Generando {fase.descripcion} ===')
        for i, (m1_idx, m2_idx) in enumerate(bracket):
            p1 = partidos_anteriores[m1_idx - 1] if m1_idx <= len(partidos_anteriores) else None
            p2 = partidos_anteriores[m2_idx - 1] if m2_idx <= len(partidos_anteriores) else None
            if not p1 or not p2:
                self.stdout.write(self.style.WARNING(f'  Partido {i+1}: aún no hay ganadores definidos.'))
                continue

            def ganador(p):
                if p.goles_totales_local > p.goles_totales_visitante:
                    return p.pais_local
                return p.pais_visitante

            local = ganador(p1)
            visitante = ganador(p2)
            msg = f'  Partido {i+1}: Gan. P{m1_idx} ({local.nombre}) vs Gan. P{m2_idx} ({visitante.nombre})'
            self.stdout.write(msg)

            if not dry_run:
                partido, c = Partido.objects.get_or_create(
                    fase=fase, pais_local=local, pais_visitante=visitante,
                    defaults={
                        'estadio': estadio,
                        'fecha': base_date + timedelta(hours=i * 6),
                        'jugado': False,
                    }
                )
                if c:
                    created += 1

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN — ningún partido creado.'))
        else:
            self.stdout.write(self.style.SUCCESS(f'✓ {created} nuevos partidos de {fase.descripcion} creados.'))

    def _generar_final(self, dry_run):
        semis = list(Partido.objects.filter(fase__id_fase=5, jugado=True).order_by('fecha', 'id'))
        if len(semis) < 2:
            self.stdout.write(self.style.WARNING('Necesitas al menos 2 semifinales jugadas.'))
            return

        estadio = Estadio.objects.first()
        base = timezone.now() + timedelta(days=90)

        def ganador(p):
            return p.pais_local if p.goles_totales_local > p.goles_totales_visitante else p.pais_visitante

        def perdedor(p):
            return p.pais_visitante if p.goles_totales_local > p.goles_totales_visitante else p.pais_local

        # 3rd place match
        fase_3rd = Fase.objects.get(id_fase=6)
        p3, c3 = Partido.objects.get_or_create(
            fase=fase_3rd,
            pais_local=perdedor(semis[0]),
            pais_visitante=perdedor(semis[1]),
            defaults={'estadio': estadio, 'fecha': base, 'jugado': False}
        )

        # Final
        fase_final = Fase.objects.get(id_fase=7)
        p_final, c_final = Partido.objects.get_or_create(
            fase=fase_final,
            pais_local=ganador(semis[0]),
            pais_visitante=ganador(semis[1]),
            defaults={'estadio': estadio, 'fecha': base + timedelta(days=4), 'jugado': False}
        )

        if not dry_run:
            self.stdout.write(self.style.SUCCESS(
                f'✓ 3er Puesto: {p3.pais_local} vs {p3.pais_visitante}\n'
                f'✓ Final: {p_final.pais_local} vs {p_final.pais_visitante}'
            ))
