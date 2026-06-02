from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.db.models import Sum, Count, Q
from django.utils import timezone
from .models import (Partido, Pronostico, Pais, Jugador, Fase, PerfilUsuario,
                     GolPartido, SeleccionJugador, MAX_JUGADORES_SELECCION,
                     torneo_iniciado, primer_partido_fecha)
from .whatsapp import normalizar_telefono as _norm_tel


def landing(request):
    """Public landing page — explains the polla, shows payment QR."""
    from .models import TorneoConfig
    torneo = TorneoConfig.get()
    return render(request, 'landing.html', {'torneo': torneo})


def custom_login(request):
    """Login that accepts either 8-digit phone (auto-prepends 591) or full username."""
    if request.user.is_authenticated:
        return redirect('polla:ranking')

    error = None
    if request.method == 'POST':
        username_raw = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')

        # Auto-prepend 591 if 8-digit number
        limpio = _norm_tel(username_raw)
        if len(limpio) == 8:
            username = '591' + limpio
        else:
            username = username_raw

        user = authenticate(request, username=username, password=password)
        if user is not None and user.is_active:
            login(request, user)
            next_url = request.GET.get('next', '/')
            return redirect(next_url)
        else:
            error = True

    return render(request, 'registration/login.html', {'form_error': error})


def custom_logout(request):
    logout(request)
    return redirect('login')
from .forms import PerfilForm


def _es_admin(user):
    return user.is_staff


def home(request):
    # Authenticated → ranking | Not authenticated → landing page
    if request.user.is_authenticated:
        return redirect('polla:ranking')
    return redirect('landing')


@login_required
def pronosticos_usuario(request, username):
    """Show ALL predictions with full point breakdown per match."""
    target = get_object_or_404(User, username=username, is_active=True)

    prons_qs = Pronostico.objects.filter(usuario=target).select_related(
        'partido__pais_local', 'partido__pais_visitante', 'partido__fase',
        'partido__estadio',
    ).order_by('partido__fecha')

    # Build desglose per prediction
    from django.db.models import Sum
    seleccion_ids = set(target.jugadores_seleccionados.values_list('jugador_id', flat=True))

    # Goleador pts per match
    goleador_por_partido = {}
    if seleccion_ids:
        goles_qs = GolPartido.objects.filter(
            jugador_id__in=seleccion_ids,
            partido_id__in=[p.partido_id for p in prons_qs],
            cantidad__gt=0,
        ).values('partido_id').annotate(total=Sum('cantidad'))
        for g in goles_qs:
            goleador_por_partido[g['partido_id']] = g['total'] * 2

    # Build enriched prediction list
    predicciones = []
    for pron in prons_qs:
        desglose = pron.calcular_desglose() if pron.partido.jugado else None
        pts_gol = goleador_por_partido.get(pron.partido_id, 0)
        total_row = (desglose['total'] if desglose else 0) + pts_gol
        predicciones.append({
            'pron': pron,
            'partido': pron.partido,
            'desglose': desglose,
            'pts_goleador': pts_gol,
            'total_row': total_row,
        })

    try:
        perfil = target.perfil
    except PerfilUsuario.DoesNotExist:
        perfil = None

    seleccion = target.jugadores_seleccionados.select_related('jugador__pais').all()

    pts_pronosticos = sum(r['desglose']['total'] for r in predicciones if r['desglose'])
    pts_goleador_total = target.jugadores_seleccionados.aggregate(t=Sum('puntos_acumulados'))['t'] or 0
    pts_campeon = perfil.puntos_campeon if perfil else 0
    pts_total = pts_pronosticos + pts_goleador_total + pts_campeon

    return render(request, 'polla/pronosticos_usuario.html', {
        'target': target,
        'perfil': perfil,
        'predicciones': predicciones,
        'seleccion': seleccion,
        'pts_pronosticos': pts_pronosticos,
        'pts_campeon': pts_campeon,
        'pts_goleador_total': pts_goleador_total,
        'pts_total': pts_total,
        'total_prons': len(predicciones),
        'jugados_prons': sum(1 for r in predicciones if r['partido'].jugado),
    })


@login_required
def reglas(request):
    return render(request, 'polla/reglas.html')


@login_required
def gran_pozo(request):
    from decimal import Decimal
    from .models import TorneoConfig

    torneo = TorneoConfig.get()
    cuota = torneo.cuota

    # Only count non-admin users with a valid 11-digit phone
    participantes = User.objects.filter(
        is_active=True, is_staff=False,
        perfil__telefono__regex=r'^\d{11}$',
    ).count()

    DESCUENTO = Decimal('0.15')   # 15% commission
    NETO_PORCENT = 1 - DESCUENTO  # 85% goes to pool

    cuota_neta = cuota * NETO_PORCENT
    total_pozo = cuota_neta * participantes

    premio_1 = total_pozo * Decimal('0.50')
    premio_2 = total_pozo * Decimal('0.35')
    premio_3 = total_pozo * Decimal('0.15')

    # Get current ranking to show who would win
    ranking = _calcular_ranking()

    # Only show podium/distribution when at least one user has points
    hay_puntos = any(d['puntos'] > 0 for d in ranking)

    # ── Tie-splitting logic ──────────────────────────────────────────────────
    # Group positions by tied points
    grupos = []
    i = 0
    while i < len(ranking) and len(grupos) < 3:
        pts = ranking[i]['puntos']
        tied = [ranking[j] for j in range(i, len(ranking)) if ranking[j]['puntos'] == pts]
        grupos.append(tied)
        i += len(tied)

    # Build prize distribution considering ties
    # Available prize pools for positions 1,2,3
    pools = [premio_1, premio_2, premio_3]
    posiciones = []  # list of {usuarios, premio_cada_uno, posicion_display}

    pool_idx = 0
    for pos_idx, grupo in enumerate(grupos):
        n = len(grupo)
        # Collect pools consumed by this tied group
        pools_consumed = pools[pool_idx:pool_idx + n]
        if not pools_consumed:
            break
        total_pool = sum(pools_consumed)
        por_persona = total_pool / n
        medal = ['🥇', '🥈', '🥉'][pos_idx] if pos_idx < 3 else ''
        posiciones.append({
            'usuarios': grupo,
            'por_persona': por_persona,
            'total_pool': total_pool,
            'n': n,
            'medal': medal,
            'pos_idx': pos_idx,
        })
        pool_idx += n

    return render(request, 'polla/gran_pozo.html', {
        'cuota': cuota,
        'cuota_neta': cuota_neta,
        'participantes': participantes,
        'total_pozo': total_pozo,
        'premio_1': premio_1,
        'premio_2': premio_2,
        'premio_3': premio_3,
        'descuento_pct': int(DESCUENTO * 100),
        'ranking': ranking[:3],
        'posiciones': posiciones,
        'hay_puntos': hay_puntos,
    })


def forgot_password(request):
    """Public page: enter 8-digit phone → new password.
    Tries WhatsApp first. If WhatsApp fails or is slow,
    shows a masked password on screen that user must reveal by tapping."""
    sent = False
    nueva_clave = None
    error = None

    if request.method == 'POST':
        from .whatsapp import normalizar_telefono, generar_password
        from .models import PerfilUsuario

        numero_raw = request.POST.get('numero', '').strip()
        numero_limpio = normalizar_telefono(numero_raw)

        if len(numero_limpio) == 8:
            telefono = '591' + numero_limpio
        elif len(numero_limpio) == 11 and numero_limpio.startswith('591'):
            telefono = numero_limpio
        else:
            error = 'Número inválido. Ingresa los 8 dígitos de tu número. Ej: 70512621'

        if not error:
            try:
                perfil = PerfilUsuario.objects.get(telefono=telefono)
                user = perfil.usuario
                if not user.is_active:
                    sent = True  # Don't reveal
                else:
                    nueva = generar_password()
                    user.set_password(nueva)
                    user.save()
                    _enviar_solo_clave(telefono, nueva)
                    sent = True
                    nueva_clave = nueva  # Shown masked on screen as backup
            except PerfilUsuario.DoesNotExist:
                sent = True  # Security: don't reveal if number exists

    return render(request, 'registration/forgot_password.html', {
        'sent': sent,
        'nueva_clave': nueva_clave,
        'error': error,
    })


def _enviar_solo_clave(telefono, clave):
    """Send ONLY the new password — short, easy to copy."""
    import requests as req
    from django.conf import settings
    api_url  = getattr(settings, 'EVOLUTION_API_URL',  '')
    api_key  = getattr(settings, 'EVOLUTION_API_KEY',  '')
    instance = getattr(settings, 'EVOLUTION_INSTANCE', '')
    app_url  = getattr(settings, 'APP_URL', 'https://www.elcarguero.com/MiPolla/')

    if not api_key:
        return

    mensaje = f"🔑 Tu nueva clave:\n\n*{clave}*\n\n{app_url}"
    try:
        req.post(
            f"{api_url}/message/sendText/{instance}",
            json={"number": f"{telefono}@s.whatsapp.net", "text": mensaje},
            headers={"apikey": api_key},
            timeout=8,
        )
    except Exception:
        pass


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
            # Champion locks when first match starts (same as player selection)
            if torneo_iniciado():
                messages.error(request, '🔒 El pronóstico de campeón está cerrado — el torneo ya inició.')
                return redirect('polla:pronosticos')
            perfil_form = PerfilForm(request.POST, instance=perfil)
            if perfil_form.is_valid():
                perfil_form.save()
                messages.success(request, '🏆 Campeón guardado.')
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

    # ALL matches: open ones first, then closed-but-unplayed, then played (at bottom)
    todos_partidos = Partido.objects.select_related('pais_local', 'pais_visitante', 'fase').order_by('fecha')
    # Sort: abierto first (True=open, False=closed/played) then by fecha
    partidos_abiertos = sorted(todos_partidos, key=lambda p: (not p.abierto, p.jugado, p.fecha or timezone.now()))

    user_pronosticos = {p.partido_id: p for p in request.user.pronosticos.all()}
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
    # Only show non-admin users who have a valid 11-digit phone number
    usuarios = User.objects.filter(
        is_active=True,
        is_staff=False,
        perfil__telefono__regex=r'^\d{11}$',
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
    proximos = Partido.objects.filter(jugado=False).select_related(
        'pais_local', 'pais_visitante', 'fase'
    ).order_by('fecha')[:4]
    recientes = Partido.objects.filter(jugado=True).select_related(
        'pais_local', 'pais_visitante'
    ).order_by('-fecha')[:4]
    user_prons = set(request.user.pronosticos.values_list('partido_id', flat=True))
    return render(request, 'polla/ranking.html', {
        'datos': datos,
        'proximos': proximos,
        'recientes': recientes,
        'user_prons': user_prons,
    })


@login_required
@user_passes_test(_es_admin)
def admin_usuarios(request):
    from .whatsapp import generar_password, normalizar_telefono, enviar_credenciales_whatsapp
    from .models import PerfilUsuario, TorneoConfig
    from decimal import Decimal, InvalidOperation

    # Handle cuota update
    if request.method == 'POST' and request.POST.get('action') == 'update_cuota':
        nueva_cuota = request.POST.get('cuota', '').strip().replace(',', '.')
        try:
            val = Decimal(nueva_cuota)
            if val <= 0:
                raise ValueError
            torneo = TorneoConfig.get()
            torneo.cuota = val
            torneo.save()
            messages.success(request, f'Cuota actualizada a Bs. {val}')
        except (InvalidOperation, ValueError):
            messages.error(request, 'Cuota inválida. Ingresa un número positivo.')
        return redirect('polla:admin_usuarios')

    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        telefono_raw = request.POST.get('telefono', '').strip()

        numero_limpio = normalizar_telefono(telefono_raw)
        # Auto-prepend 591 if user entered only 8 digits
        if len(numero_limpio) == 8:
            telefono = '591' + numero_limpio
        elif len(numero_limpio) == 11 and numero_limpio.startswith('591'):
            telefono = numero_limpio
        else:
            telefono = numero_limpio  # Will fail validation below

        nombre_completo = f"{first_name} {last_name}".strip()

        error = None
        if not first_name:
            error = 'El nombre es requerido.'
        elif len(telefono) != 11 or not telefono.startswith('591'):
            error = f'Ingresa los 8 dígitos del número (sin el 591). Ej: 70512621'
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

    from django.conf import settings as djsettings
    usuarios = User.objects.filter(is_staff=False).select_related('perfil').order_by('last_name', 'first_name')
    torneo_cfg = TorneoConfig.get()
    return render(request, 'polla/admin_usuarios.html', {
        'usuarios': usuarios,
        'cuota_actual': torneo_cfg.cuota,
        'wa_url':      getattr(djsettings, 'EVOLUTION_API_URL',  'http://elcarguero_evolution:8080'),
        'wa_instance': getattr(djsettings, 'EVOLUTION_INSTANCE', 'elcarguero'),
        'wa_key_ok':   bool(getattr(djsettings, 'EVOLUTION_API_KEY', '')),
    })


@login_required
@user_passes_test(_es_admin)
def admin_generar_eliminatorias(request):
    """Generate knockout round matches from group results."""
    from django.core.management import call_command
    from io import StringIO

    fase = request.GET.get('fase', 'R32')
    out = StringIO()
    try:
        call_command('generar_eliminatorias', fase=fase, stdout=out)
        messages.success(request, f'✅ {out.getvalue()}')
    except Exception as e:
        messages.error(request, f'❌ Error: {e}')
    return redirect('polla:admin_resultados')


@login_required
@user_passes_test(_es_admin)
def admin_test_whatsapp(request):
    from .whatsapp import verificar_conexion
    ok, msg = verificar_conexion()
    if ok:
        messages.success(request, f'✅ {msg}')
    else:
        messages.error(request, f'❌ {msg}')
    return redirect('polla:admin_usuarios')


@login_required
@user_passes_test(_es_admin)
def admin_registrar_webhook(request):
    from .whatsapp import registrar_webhook
    from django.conf import settings as djsettings
    app_url = getattr(djsettings, 'APP_URL', 'https://www.elcarguero.com/MiPolla/')
    webhook_url = app_url.rstrip('/') + '/webhook/whatsapp/'
    ok, msg = registrar_webhook(webhook_url)
    if ok:
        messages.success(request, f'✅ {msg}')
    else:
        messages.error(request, f'❌ {msg}')
    return redirect('polla:admin_usuarios')


from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import json


@csrf_exempt
def webhook_whatsapp(request):
    """
    Router webhook: receives all messages from Evolution API.
    - "clave" → generates new password, sends it via WA, does NOT forward.
    - Everything else → forwarded to the original ElCarguero backend webhook.
    """
    import threading
    from django.conf import settings as djsettings

    if request.method != 'POST':
        return JsonResponse({'ok': True})

    # Verify API key (Evolution sends it as header)
    api_key = getattr(djsettings, 'EVOLUTION_API_KEY', '')
    if api_key:
        if request.headers.get('apikey', '') != api_key:
            return JsonResponse({'error': 'unauthorized'}, status=401)

    raw_body = request.body
    try:
        body = json.loads(raw_body)
    except Exception:
        return _forward_to_elcarguero(raw_body)

    event = body.get('event', '')
    data  = body.get('data', {})
    key   = data.get('key', {})

    # Forward non-message events immediately to ElCarguero
    if event not in ('messages.upsert', 'MESSAGES_UPSERT'):
        return _forward_to_elcarguero(raw_body)

    # Skip own messages and groups — forward to ElCarguero
    if key.get('fromMe') or '@g.us' in key.get('remoteJid', ''):
        return _forward_to_elcarguero(raw_body)

    msg_obj = data.get('message', {})
    texto = (
        msg_obj.get('conversation') or
        msg_obj.get('extendedTextMessage', {}).get('text') or
        ''
    ).strip().lower()

    # "clave" keyword disabled — use Forgot Password page instead
    # (WhatsApp bot responses removed to avoid confusion)
    if texto == 'clave':
        return JsonResponse({'ok': True, 'ignored': 'use forgot-password page'})

    # ── Everything else → forward to ElCarguero backend ──
    return _forward_to_elcarguero(raw_body)


def _forward_to_elcarguero(raw_body: bytes):
    """Proxy the payload to the original ElCarguero webhook (non-blocking)."""
    import threading, requests as req
    ELCARGUERO_WH = 'http://elcarguero_backend:4000/api/webhook/whatsapp'

    def _send():
        try:
            req.post(ELCARGUERO_WH, data=raw_body,
                     headers={'Content-Type': 'application/json'}, timeout=8)
        except Exception:
            pass

    threading.Thread(target=_send, daemon=True).start()
    return JsonResponse({'ok': True, 'forwarded': True})


@login_required
@user_passes_test(_es_admin)
def admin_reset_password(request, pk):
    """Admin-only: reset user password.
    Admin can choose generic 'Polla2026' or generate a random one.
    Password shown ONLY to admin, also tries WhatsApp."""
    user = get_object_or_404(User, pk=pk)
    from .whatsapp import generar_password

    tipo = request.POST.get('tipo', 'random')
    if tipo == 'generic':
        nueva = 'Polla2026'
    else:
        nueva = generar_password()

    user.set_password(nueva)
    user.save()

    nombre = user.get_full_name() or user.username
    wa_status = '❌ no enviado'
    try:
        telefono = user.perfil.telefono
        if telefono and len(telefono) == 11:
            _enviar_solo_clave(telefono, nueva)
            wa_status = f'✅ WA enviado a +{telefono}'
    except Exception:
        pass

    messages.success(
        request,
        f'🔑 <strong>{nombre}</strong> — Clave: '
        f'<code style="font-size:1.1rem;font-weight:900;letter-spacing:2px;'
        f'background:rgba(29,78,216,.15);padding:.15rem .6rem;border-radius:6px;">{nueva}</code> '
        f'— {wa_status}'
    )
    return redirect('polla:admin_usuarios')


@login_required
@user_passes_test(_es_admin)
def admin_eliminar_usuario(request, pk):
    """Permanently delete a user — removes them from ranking and pool."""
    if request.method != 'POST':
        return redirect('polla:admin_usuarios')
    user = get_object_or_404(User, pk=pk, is_staff=False)
    nombre = user.get_full_name() or user.username
    user.delete()
    messages.success(request, f'Usuario "{nombre}" eliminado permanentemente.')
    return redirect('polla:admin_usuarios')


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

    # Flat list: ALL pending matches first (asc by date), then ALL played (asc by date)
    todos = list(Partido.objects.select_related(
        'fase', 'pais_local', 'pais_visitante',
    ).prefetch_related('goles__jugador__pais').all())

    partidos_ordenados = sorted(
        todos,
        key=lambda p: (p.jugado, p.fecha or timezone.now())
    )

    partidos_con_jugadores = {}
    for partido in partidos_ordenados:
        jugadores = list(Jugador.objects.filter(
            Q(pais=partido.pais_local) | Q(pais=partido.pais_visitante)
        ).select_related('pais').order_by('pais__nombre', 'nombre_completo'))
        goles_existentes = {g.jugador_id: g.cantidad for g in partido.goles.all()}
        partidos_con_jugadores[partido.id] = {
            'jugadores': jugadores,
            'goles': goles_existentes,
        }

    return render(request, 'polla/admin_resultados.html', {
        'partidos_ordenados': partidos_ordenados,
        'partidos_con_jugadores': partidos_con_jugadores,
    })
