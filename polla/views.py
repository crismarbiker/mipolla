from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Sum, Count, Q
from django.utils import timezone
from .models import (Partido, Pronostico, Pais, Jugador, Fase, PerfilUsuario,
                     GolPartido, SeleccionJugador, MAX_JUGADORES_SELECCION)
from .forms import ResultadoForm, PerfilForm


def _es_admin(user):
    return user.is_staff


@login_required
def home(request):
    proximos = Partido.objects.filter(jugado=False).select_related(
        'pais_local', 'pais_visitante', 'fase'
    ).order_by('fecha')[:6]

    recientes = Partido.objects.filter(jugado=True).select_related(
        'pais_local', 'pais_visitante'
    ).order_by('-fecha')[:6]

    user_pronosticos = set(request.user.pronosticos.values_list('partido_id', flat=True))
    top_ranking = _calcular_ranking()[:5]

    user_pos = None
    for i, d in enumerate(top_ranking):
        if d['usuario'] == request.user:
            user_pos = i + 1
            break

    return render(request, 'polla/home.html', {
        'proximos': proximos,
        'recientes': recientes,
        'user_pronosticos': user_pronosticos,
        'top_ranking': top_ranking,
        'user_pos': user_pos,
    })


@login_required
def partidos(request):
    fases = Fase.objects.prefetch_related(
        'partidos__pais_local',
        'partidos__pais_visitante',
        'partidos__estadio',
    ).all()
    user_pronosticos = {p.partido_id: p for p in request.user.pronosticos.all()}
    return render(request, 'polla/partidos.html', {
        'fases': fases,
        'user_pronosticos': user_pronosticos,
    })


@login_required
def pronosticos(request):
    perfil, _ = PerfilUsuario.objects.get_or_create(usuario=request.user)
    seleccion_actual = list(request.user.jugadores_seleccionados.select_related('jugador__pais'))

    if request.method == 'POST':
        action = request.POST.get('action', 'pronosticos')

        if action == 'jugadores':
            # Save player selection (up to 5)
            ids_raw = request.POST.getlist('jugador_ids')
            try:
                ids = [int(x) for x in ids_raw if x.strip()]
            except ValueError:
                ids = []

            if len(ids) > MAX_JUGADORES_SELECCION:
                messages.error(request, f'Solo puedes seleccionar hasta {MAX_JUGADORES_SELECCION} jugadores.')
            else:
                jugadores_validos = Jugador.objects.filter(pk__in=ids)
                # Delete old selections and recreate
                request.user.jugadores_seleccionados.all().delete()
                for j in jugadores_validos:
                    pts = j.total_goles * 2  # recalculate from existing goals
                    SeleccionJugador.objects.create(usuario=request.user, jugador=j, puntos_acumulados=pts)
                messages.success(request, f'{len(jugadores_validos)} jugador(es) seleccionado(s).')
            return redirect('polla:pronosticos')

        if action == 'campeon':
            # Save champion prediction
            perfil_form = PerfilForm(request.POST, instance=perfil)
            if perfil_form.is_valid():
                perfil_form.save()
                messages.success(request, 'Pronóstico de campeón guardado.')
            return redirect('polla:pronosticos')

        # Default: save match predictions
        partidos_abiertos = Partido.objects.filter(jugado=False)
        saved = 0
        for partido in partidos_abiertos:
            if not partido.abierto:
                continue
            try:
                gl = int(request.POST.get(f'gl_{partido.id}', -1))
                gv = int(request.POST.get(f'gv_{partido.id}', -1))
                if gl < 0 or gv < 0:
                    continue
                predice_penales = bool(request.POST.get(f'pen_{partido.id}')) and partido.es_eliminatoria
                Pronostico.objects.update_or_create(
                    usuario=request.user,
                    partido=partido,
                    defaults={
                        'goles_local': gl,
                        'goles_visitante': gv,
                        'predice_penales': predice_penales,
                    },
                )
                saved += 1
            except (ValueError, TypeError):
                pass
        messages.success(request, f'{saved} pronóstico(s) guardado(s).')
        return redirect('polla:pronosticos')

    partidos_abiertos = Partido.objects.filter(jugado=False).select_related(
        'pais_local', 'pais_visitante', 'fase'
    ).order_by('fecha')

    user_pronosticos = {p.partido_id: p for p in request.user.pronosticos.filter(partido__jugado=False)}
    perfil_form = PerfilForm(instance=perfil)

    # All players grouped by country for the selection UI
    paises_con_jugadores = Pais.objects.prefetch_related('jugadores').order_by('grupo', 'nombre')
    ids_seleccionados = set(s.jugador_id for s in seleccion_actual)

    return render(request, 'polla/pronosticos.html', {
        'partidos': partidos_abiertos,
        'user_pronosticos': user_pronosticos,
        'perfil_form': perfil_form,
        'perfil': perfil,
        'seleccion_actual': seleccion_actual,
        'ids_seleccionados': ids_seleccionados,
        'paises_con_jugadores': paises_con_jugadores,
        'max_jugadores': MAX_JUGADORES_SELECCION,
    })


def _calcular_ranking():
    usuarios = User.objects.filter(
        is_active=True, is_staff=False
    ).prefetch_related('pronosticos', 'perfil', 'jugadores_seleccionados')

    datos = []
    for u in usuarios:
        try:
            perfil = u.perfil
        except PerfilUsuario.DoesNotExist:
            perfil = PerfilUsuario(usuario=u)

        qs = u.pronosticos.filter(partido__jugado=True)
        puntos_base = qs.aggregate(t=Sum('puntos'))['t'] or 0
        exactos = qs.filter(puntos__gte=3).count()
        acertados = qs.filter(puntos=2).count()
        jugados = qs.count()
        pts_jugadores = u.jugadores_seleccionados.aggregate(t=Sum('puntos_acumulados'))['t'] or 0

        datos.append({
            'usuario': u,
            'puntos': puntos_base + perfil.puntos_campeon + pts_jugadores,
            'exactos': exactos,
            'acertados': acertados,
            'jugados': jugados,
            'campeon': perfil.campeon,
            'pts_jugadores': pts_jugadores,
        })

    datos.sort(key=lambda x: (-x['puntos'], -x['exactos'], -x['acertados']))
    return datos


@login_required
def ranking(request):
    datos = _calcular_ranking()
    return render(request, 'polla/ranking.html', {'datos': datos})


@login_required
@user_passes_test(_es_admin)
def admin_usuarios(request):
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password1 = request.POST.get('password1', '')
        password2 = request.POST.get('password2', '')
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip()

        error = None
        if not username:
            error = 'El nombre de usuario es requerido.'
        elif User.objects.filter(username=username).exists():
            error = f'El usuario "{username}" ya existe.'
        elif password1 != password2:
            error = 'Las contraseñas no coinciden.'
        elif len(password1) < 8:
            error = 'La contraseña debe tener al menos 8 caracteres.'

        if error:
            messages.error(request, error)
        else:
            user = User.objects.create_user(
                username=username, password=password1,
                first_name=first_name, last_name=last_name, email=email,
            )
            messages.success(request, f'Usuario "{user.get_full_name() or username}" creado exitosamente.')
            return redirect('polla:admin_usuarios')

    usuarios = User.objects.filter(is_staff=False).order_by('last_name', 'first_name')
    return render(request, 'polla/admin_usuarios.html', {'usuarios': usuarios})


@login_required
@user_passes_test(_es_admin)
def admin_toggle_usuario(request, pk):
    user = get_object_or_404(User, pk=pk, is_staff=False)
    user.is_active = not user.is_active
    user.save()
    estado = 'activado' if user.is_active else 'desactivado'
    messages.success(request, f'Usuario "{user.username}" {estado}.')
    return redirect('polla:admin_usuarios')


@login_required
@user_passes_test(_es_admin)
def admin_resultados(request):
    if request.method == 'POST':
        partido_id = request.POST.get('partido_id')
        partido = get_object_or_404(Partido, pk=partido_id)
        form = ResultadoForm(request.POST, instance=partido)

        if form.is_valid():
            partido = form.save(commit=False)
            partido.jugado = True
            partido.save()

            # Recalculate match prediction points
            for pron in partido.pronosticos.all():
                pron.puntos = pron.calcular_puntos()
                pron.save()

            # Register goals per player
            # POST contains: goles_jugador_<jugador_id> = cantidad (may be 0 or missing)
            jugadores_partido = Jugador.objects.filter(
                Q(pais=partido.pais_local) | Q(pais=partido.pais_visitante)
            )
            for jugador in jugadores_partido:
                key = f'goles_jugador_{jugador.id}'
                raw = request.POST.get(key, '').strip()
                if not raw:
                    continue
                try:
                    cantidad = int(raw)
                except ValueError:
                    continue
                if cantidad > 0:
                    gol, _ = GolPartido.objects.update_or_create(
                        jugador=jugador,
                        partido=partido,
                        defaults={'cantidad': cantidad},
                    )
                    gol.recalcular_bonus_jugador()
                else:
                    # Remove existing goal record if set to 0
                    GolPartido.objects.filter(jugador=jugador, partido=partido).delete()
                    # Recalculate (total may have changed)
                    fake = GolPartido(jugador=jugador, partido=partido, cantidad=0)
                    fake.recalcular_bonus_jugador()

            # If final, set champion and award points
            if partido.fase_id == 7 and partido.goles_local is not None:
                campeon = partido.pais_local if (
                    partido.goles_totales_local > partido.goles_totales_visitante
                ) else partido.pais_visitante
                Pais.objects.update(es_campeon=False)
                campeon.es_campeon = True
                campeon.save()
                for perfil in PerfilUsuario.objects.filter(campeon=campeon):
                    perfil.puntos_campeon = 15
                    perfil.save()

            messages.success(request, f'Resultado guardado: {partido} {partido.resultado_str}')
            return redirect('polla:admin_resultados')

    fases = Fase.objects.prefetch_related(
        'partidos__pais_local',
        'partidos__pais_visitante',
        'partidos__goles__jugador',
    ).all()

    # Pre-load players per country for the goal entry forms
    from django.db.models import Prefetch
    partidos_con_jugadores = {}
    for fase in fases:
        for partido in fase.partidos.all():
            jugadores = list(Jugador.objects.filter(
                Q(pais=partido.pais_local) | Q(pais=partido.pais_visitante)
            ).select_related('pais').order_by('pais', 'nombre_completo'))
            goles_existentes = {g.jugador_id: g.cantidad for g in partido.goles.all()}
            partidos_con_jugadores[partido.id] = {
                'jugadores': jugadores,
                'goles': goles_existentes,
            }

    return render(request, 'polla/admin_resultados.html', {
        'fases': fases,
        'partidos_con_jugadores': partidos_con_jugadores,
    })
