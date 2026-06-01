from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Sum, Count, Q
from django.utils import timezone
from .models import (Partido, Pronostico, Pais, Jugador, Fase, PerfilUsuario,
                     GolPartido, SeleccionJugador, MAX_JUGADORES_SELECCION,
                     torneo_iniciado, primer_partido_fecha)
from .forms import PerfilForm


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
            # LOCK: player selection closes when first match starts
            if torneo_iniciado():
                messages.error(request, 'La selección de jugadores está cerrada — el torneo ya inició.')
                return redirect('polla:pronosticos')

            ids_raw = request.POST.getlist('jugador_ids')
            try:
                ids = [int(x) for x in ids_raw if x.strip()]
            except ValueError:
                ids = []

            if len(ids) > MAX_JUGADORES_SELECCION:
                messages.error(request, f'Solo puedes seleccionar hasta {MAX_JUGADORES_SELECCION} jugadores.')
            else:
                jugadores_validos = Jugador.objects.filter(pk__in=ids)
                request.user.jugadores_seleccionados.all().delete()
                for j in jugadores_validos:
                    pts = j.total_goles * 2
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
        omitidos = 0
        for partido in partidos_abiertos:
            if not partido.abierto:
                omitidos += 1
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
        msg = f'{saved} pronóstico(s) guardado(s).'
        if omitidos:
            msg += f' ({omitidos} partido(s) ya iniciado(s) no se modificaron.)'
        messages.success(request, msg)
        return redirect('polla:pronosticos')

    partidos_abiertos = Partido.objects.filter(jugado=False).select_related(
        'pais_local', 'pais_visitante', 'fase'
    ).order_by('fecha')

    user_pronosticos = {p.partido_id: p for p in request.user.pronosticos.filter(partido__jugado=False)}
    perfil_form = PerfilForm(instance=perfil)

    # All players grouped by country for the selection UI
    paises_con_jugadores = Pais.objects.prefetch_related('jugadores').order_by('grupo', 'nombre')
    ids_seleccionados = set(s.jugador_id for s in seleccion_actual)
    jugadores_bloqueados = torneo_iniciado()
    primer_partido = primer_partido_fecha()

    return render(request, 'polla/pronosticos.html', {
        'partidos': partidos_abiertos,
        'user_pronosticos': user_pronosticos,
        'perfil_form': perfil_form,
        'perfil': perfil,
        'seleccion_actual': seleccion_actual,
        'ids_seleccionados': ids_seleccionados,
        'paises_con_jugadores': paises_con_jugadores,
        'max_jugadores': MAX_JUGADORES_SELECCION,
        'jugadores_bloqueados': jugadores_bloqueados,
        'primer_partido': primer_partido,
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
    from .whatsapp import generar_password, normalizar_telefono, enviar_credenciales_whatsapp
    from .models import PerfilUsuario

    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        telefono_raw = request.POST.get('telefono', '').strip()

        telefono = normalizar_telefono(telefono_raw)
        nombre_completo = f"{first_name} {last_name}".strip()

        error = None
        if not first_name:
            error = 'El nombre es requerido.'
        elif not telefono or len(telefono) < 8:
            error = 'Número de teléfono inválido (ingresa el número completo con código de país).'
        elif User.objects.filter(username=telefono).exists():
            error = f'Ya existe un usuario con el número {telefono}.'

        if error:
            messages.error(request, error)
        else:
            password = generar_password()
            user = User.objects.create_user(
                username=telefono,
                password=password,
                first_name=first_name,
                last_name=last_name,
            )
            # Save phone in profile
            perfil = user.perfil
            perfil.telefono = telefono
            perfil.save()

            # Send WhatsApp
            ok, wa_msg = enviar_credenciales_whatsapp(telefono, nombre_completo, telefono, password)
            if ok:
                messages.success(request, f'✅ Usuario "{nombre_completo}" creado. {wa_msg}')
            else:
                messages.warning(
                    request,
                    f'⚠️ Usuario "{nombre_completo}" creado pero no se pudo enviar WhatsApp: {wa_msg} — '
                    f'Contraseña: <code>{password}</code>'
                )
            return redirect('polla:admin_usuarios')

    usuarios = User.objects.filter(is_staff=False).select_related('perfil').order_by('last_name', 'first_name')
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
def admin_fetch_resultado(request, pk):
    """Fetch result from football-data.org for a single match and apply it."""
    from .fetch_results import fetch_match_result
    from django.conf import settings

    partido = get_object_or_404(Partido, pk=pk, jugado=False)

    if not getattr(settings, 'FOOTBALL_DATA_API_KEY', ''):
        messages.error(request, 'No está configurada la API key de football-data.org (FOOTBALL_DATA_API_KEY).')
        return redirect('polla:admin_resultados')

    if not partido.fd_match_id:
        messages.error(request, f'El partido {partido} no tiene ID de football-data.org configurado.')
        return redirect('polla:admin_resultados')

    data = fetch_match_result(partido.fd_match_id)
    if not data:
        messages.error(request, f'No se pudo obtener el resultado para {partido} (API no disponible o partido sin terminar).')
        return redirect('polla:admin_resultados')

    if data.get('status') not in ('FINISHED',):
        messages.warning(request, f'El partido {partido} aún no ha terminado (estado: {data.get("status")}).')
        return redirect('polla:admin_resultados')

    if data.get('home') is None:
        messages.error(request, f'La API no devolvió marcador para {partido}.')
        return redirect('polla:admin_resultados')

    partido.goles_local = data['home']
    partido.goles_visitante = data['away']
    partido.hubo_penales = data.get('hubo_penales', False)
    partido.penales_local = data.get('pen_home')
    partido.penales_visitante = data.get('pen_away')
    partido.jugado = True
    partido.save()

    for pron in partido.pronosticos.all():
        pron.puntos = pron.calcular_puntos()
        pron.save()

    if partido.fase_id == 7 and partido.goles_local is not None:
        campeon = partido.pais_local if partido.goles_totales_local > partido.goles_totales_visitante else partido.pais_visitante
        Pais.objects.update(es_campeon=False)
        campeon.es_campeon = True
        campeon.save()
        for perfil in PerfilUsuario.objects.filter(campeon=campeon):
            perfil.puntos_campeon = 15
            perfil.save()

    messages.success(request, f'✅ Resultado obtenido automáticamente: {partido} {partido.resultado_str}')
    return redirect('polla:admin_resultados')


@login_required
@user_passes_test(_es_admin)
def admin_resultados(request):
    if request.method == 'POST':
        partido_id = request.POST.get('partido_id')
        partido = get_object_or_404(Partido, pk=partido_id)

        # ── 1. Collect player goals from POST ──────────────────────────────
        jugadores_local = list(Jugador.objects.filter(pais=partido.pais_local))
        jugadores_visitante = list(Jugador.objects.filter(pais=partido.pais_visitante))
        ids_local = {j.id for j in jugadores_local}
        ids_visitante = {j.id for j in jugadores_visitante}

        goles_local_calc = 0
        goles_visitante_calc = 0
        goals_data = {}   # jugador_id → cantidad (signed)

        for jugador in jugadores_local + jugadores_visitante:
            raw = request.POST.get(f'goles_jugador_{jugador.id}', '').strip()
            if not raw:
                continue
            try:
                cantidad = int(raw)
            except ValueError:
                continue
            if cantidad == 0:
                continue
            goals_data[jugador.id] = cantidad

            # Own goal (negative) scores for the opponent
            if jugador.id in ids_local:
                if cantidad > 0:
                    goles_local_calc += cantidad
                else:
                    goles_visitante_calc += abs(cantidad)  # own goal → visitor
            else:
                if cantidad > 0:
                    goles_visitante_calc += cantidad
                else:
                    goles_local_calc += abs(cantidad)      # own goal → local

        # ── 2. Handle penalties (knockout rounds only) ──────────────────────
        hubo_penales = bool(request.POST.get('hubo_penales'))
        penales_local = None
        penales_visitante = None
        if hubo_penales:
            try:
                penales_local = int(request.POST.get('penales_local', 0))
                penales_visitante = int(request.POST.get('penales_visitante', 0))
            except (ValueError, TypeError):
                hubo_penales = False

        # ── 3. Save match result ─────────────────────────────────────────────
        partido.goles_local = goles_local_calc
        partido.goles_visitante = goles_visitante_calc
        partido.hubo_penales = hubo_penales
        partido.penales_local = penales_local
        partido.penales_visitante = penales_visitante
        partido.jugado = True
        partido.save()

        # ── 4. Save individual goal records ─────────────────────────────────
        affected_jugadores = set()
        for jugador_id, cantidad in goals_data.items():
            jugador = Jugador.objects.get(pk=jugador_id)
            GolPartido.objects.update_or_create(
                jugador=jugador,
                partido=partido,
                defaults={'cantidad': cantidad},
            )
            affected_jugadores.add(jugador)

        # Remove zeroed-out or blank entries
        GolPartido.objects.filter(
            partido=partido
        ).exclude(jugador_id__in=goals_data.keys()).delete()

        # Recalculate bonus for all affected players
        for jugador in affected_jugadores:
            gol_obj = GolPartido.objects.get(jugador=jugador, partido=partido)
            gol_obj.recalcular_bonus_jugador()

        # Also recalculate for players whose records were removed
        removed = Jugador.objects.filter(
            pais__in=[partido.pais_local, partido.pais_visitante]
        ).exclude(id__in=goals_data.keys())
        for jugador in removed:
            # Their total may have changed if we deleted a record; recalculate
            fake = GolPartido(jugador=jugador, partido=partido, cantidad=0)
            fake.recalcular_bonus_jugador()

        # ── 5. Recalculate prediction points ────────────────────────────────
        for pron in partido.pronosticos.all():
            pron.puntos = pron.calcular_puntos()
            pron.save()

        # ── 6. Final: set champion ───────────────────────────────────────────
        if partido.fase_id == 7:
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
