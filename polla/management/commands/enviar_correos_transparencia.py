"""
Envia un correo de transparencia a los participantes que activaron el opt-in
justo cuando un partido inicia (su 'fecha' ya pasó), mostrando los pronosticos
de TODOS para ese partido — prueba de que nadie los cambio despues del cierre.

Antes del primer partido del torneo, envia un correo especial adicional con
los jugadores seleccionados y campeones elegidos por cada participante,
ademas de los pronosticos del primer partido.

Pensado para correr cada 1-2 minutos via cron:
  python manage.py enviar_correos_transparencia
"""
from django.conf import settings
from django.contrib.auth.models import User
from django.core.mail import EmailMessage
from django.core.management.base import BaseCommand
from django.utils import timezone

from polla.models import Partido, Pronostico, PerfilUsuario, TorneoConfig


class Command(BaseCommand):
    help = 'Envia correos de transparencia al cierre de cada partido'

    def handle(self, *args, **options):
        ahora = timezone.now()
        partidos = list(
            Partido.objects.filter(fecha__isnull=False, fecha__lte=ahora, correo_enviado=False)
            .select_related('pais_local', 'pais_visitante', 'fase')
            .order_by('fecha', 'id')
        )

        if not partidos:
            self.stdout.write('No hay partidos pendientes de notificar.')
            return

        destinatarios = list(
            User.objects.filter(perfil__recibir_correos=True)
            .exclude(email='')
            .values_list('email', flat=True)
        )

        primer_partido = Partido.objects.filter(fecha__isnull=False).order_by('fecha', 'id').first()
        torneo = TorneoConfig.get()

        for partido in partidos:
            es_primer_partido = primer_partido and partido.id == primer_partido.id

            if es_primer_partido and not torneo.correo_apertura_enviado:
                self._enviar_correo_apertura(partido, destinatarios)
                torneo.correo_apertura_enviado = True
                torneo.save(update_fields=['correo_apertura_enviado'])
            else:
                self._enviar_correo_partido(partido, destinatarios)

            partido.correo_enviado = True
            partido.save(update_fields=['correo_enviado'])
            self.stdout.write(self.style.SUCCESS(f'Correo enviado: {partido}'))

    def _pronosticos_texto(self, partido):
        prons = (
            Pronostico.objects.filter(partido=partido)
            .select_related('usuario')
            .order_by('usuario__first_name', 'usuario__last_name')
        )
        if not prons:
            return '  (nadie pronosticó este partido)'
        lineas = []
        for p in prons:
            nombre = p.usuario.get_full_name() or p.usuario.username
            linea = f'  - {nombre}: {p.goles_local}-{p.goles_visitante}'
            if p.predice_penales:
                linea += ' (predice penales)'
            lineas.append(linea)
        return '\n'.join(lineas)

    def _enviar_correo_partido(self, partido, destinatarios):
        if not destinatarios:
            return
        asunto = f'🔒 Pronósticos cerrados: {partido.pais_local} vs {partido.pais_visitante}'
        cuerpo = (
            f'El partido {partido.pais_local} vs {partido.pais_visitante} ({partido.fase.descripcion}) '
            f'acaba de iniciar.\n\n'
            f'Estos son los pronósticos de todos los participantes, congelados antes del arranque:\n\n'
            f'{self._pronosticos_texto(partido)}\n\n'
            f'— Mi Polla 2026 (correo automático de transparencia)'
        )
        self._enviar(asunto, cuerpo, destinatarios)

    def _enviar_correo_apertura(self, primer_partido, destinatarios):
        if not destinatarios:
            return
        lineas_jugadores = []
        usuarios_con_seleccion = (
            User.objects.filter(jugadores_seleccionados__isnull=False)
            .distinct()
            .order_by('first_name', 'last_name')
        )
        for usuario in usuarios_con_seleccion:
            jugadores = usuario.jugadores_seleccionados.select_related('jugador__pais')
            nombres = ', '.join(f'{s.jugador.nombre_completo} ({s.jugador.pais.nombre})' for s in jugadores)
            nombre_usuario = usuario.get_full_name() or usuario.username
            lineas_jugadores.append(f'  - {nombre_usuario}: {nombres or "(sin jugadores)"}')

        lineas_campeones = []
        perfiles_con_campeon = (
            PerfilUsuario.objects.filter(campeon__isnull=False)
            .select_related('usuario', 'campeon')
            .order_by('usuario__first_name', 'usuario__last_name')
        )
        for perfil in perfiles_con_campeon:
            nombre_usuario = perfil.usuario.get_full_name() or perfil.usuario.username
            lineas_campeones.append(f'  - {nombre_usuario}: {perfil.campeon.nombre}')

        asunto = '🏆 Arranca el torneo — Jugadores, Campeones y primer partido'
        cuerpo = (
            'El torneo está a punto de iniciar. Antes del primer partido, esto es lo que cada '
            'participante eligió (congelado, transparente y verificable):\n\n'
            'JUGADORES SELECCIONADOS:\n'
            + ('\n'.join(lineas_jugadores) or '  (nadie seleccionó jugadores)')
            + '\n\n'
            'CAMPEONES ELEGIDOS:\n'
            + ('\n'.join(lineas_campeones) or '  (nadie eligió campeón)')
            + '\n\n'
            f'PRIMER PARTIDO: {primer_partido.pais_local} vs {primer_partido.pais_visitante}\n'
            f'{self._pronosticos_texto(primer_partido)}\n\n'
            '— Mi Polla 2026 (correo automático de transparencia)'
        )
        self._enviar(asunto, cuerpo, destinatarios)

    def _enviar(self, asunto, cuerpo, destinatarios):
        remitente = settings.DEFAULT_FROM_EMAIL
        to_placeholder = remitente.split('<')[-1].rstrip('>') if '<' in remitente else remitente
        msg = EmailMessage(
            subject=asunto,
            body=cuerpo,
            from_email=remitente,
            to=[to_placeholder],
            bcc=destinatarios,
        )
        msg.send(fail_silently=False)
