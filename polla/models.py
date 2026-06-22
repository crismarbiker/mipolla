from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

LETRA_GRUPO = {1: 'A', 2: 'B', 3: 'C', 4: 'D', 5: 'E', 6: 'F',
               7: 'G', 8: 'H', 9: 'I', 10: 'J', 11: 'K', 12: 'L'}

MAX_JUGADORES_SELECCION = 5
PUNTOS_POR_GOL = 2


def torneo_iniciado() -> bool:
    """Returns True once the first scheduled match has started."""
    primer = Partido.objects.filter(fecha__isnull=False).order_by('fecha').first()
    if not primer:
        return False
    return timezone.now() >= primer.fecha


def primer_partido_fecha():
    """Returns the datetime of the first match, or None."""
    primer = Partido.objects.filter(fecha__isnull=False).order_by('fecha').first()
    return primer.fecha if primer else None


class Fase(models.Model):
    id_fase = models.SmallIntegerField(primary_key=True)
    descripcion = models.CharField(max_length=50)

    class Meta:
        ordering = ['id_fase']
        verbose_name = 'Fase'
        verbose_name_plural = 'Fases'

    def __str__(self):
        return self.descripcion


class Estadio(models.Model):
    nombre = models.CharField(max_length=100)

    class Meta:
        ordering = ['nombre']
        verbose_name = 'Estadio'
        verbose_name_plural = 'Estadios'

    def __str__(self):
        return self.nombre


class Pais(models.Model):
    nombre = models.CharField(max_length=60)
    grupo = models.SmallIntegerField()
    imagen = models.ImageField(upload_to='flags/', null=True, blank=True)
    es_campeon = models.BooleanField(default=False)
    emoji = models.CharField(max_length=10, blank=True)

    class Meta:
        ordering = ['grupo', 'nombre']
        verbose_name = 'País'
        verbose_name_plural = 'Países'

    @property
    def letra_grupo(self):
        return LETRA_GRUPO.get(self.grupo, '?')

    def __str__(self):
        return self.nombre


class Jugador(models.Model):
    pais = models.ForeignKey(Pais, on_delete=models.CASCADE, related_name='jugadores')
    nombre_completo = models.CharField(max_length=120)
    edad = models.SmallIntegerField()

    class Meta:
        ordering = ['pais', 'nombre_completo']
        verbose_name = 'Jugador'
        verbose_name_plural = 'Jugadores'

    @property
    def total_goles(self):
        """Count only positive goals (own goals excluded)."""
        from django.db.models import Sum
        return self.goles_anotados.filter(cantidad__gt=0).aggregate(t=Sum('cantidad'))['t'] or 0

    def __str__(self):
        return f"{self.nombre_completo} ({self.pais.nombre})"


FASES_ELIMINACION = {2, 3, 4, 5, 6, 7}


class Partido(models.Model):
    fase = models.ForeignKey(Fase, on_delete=models.PROTECT, related_name='partidos')
    estadio = models.ForeignKey(Estadio, on_delete=models.SET_NULL, null=True, blank=True)
    pais_local = models.ForeignKey(Pais, on_delete=models.PROTECT, related_name='partidos_local')
    pais_visitante = models.ForeignKey(Pais, on_delete=models.PROTECT, related_name='partidos_visitante')
    fecha = models.DateTimeField(null=True, blank=True)
    goles_local = models.SmallIntegerField(null=True, blank=True)
    goles_visitante = models.SmallIntegerField(null=True, blank=True)
    hubo_penales = models.BooleanField(default=False)
    penales_local = models.SmallIntegerField(null=True, blank=True)
    penales_visitante = models.SmallIntegerField(null=True, blank=True)
    jugado = models.BooleanField(default=False)
    # football-data.org match ID for automatic result fetching (optional)
    fd_match_id = models.IntegerField(null=True, blank=True, verbose_name='football-data.org ID')
    correo_enviado = models.BooleanField(default=False,
                                         help_text='Si ya se envió el correo de transparencia con los pronósticos al cierre de este partido')

    class Meta:
        ordering = ['fecha', 'id']
        verbose_name = 'Partido'
        verbose_name_plural = 'Partidos'

    @property
    def abierto(self):
        if not self.fecha:
            return not self.jugado
        return timezone.now() < self.fecha and not self.jugado

    @property
    def es_eliminatoria(self):
        return self.fase_id in FASES_ELIMINACION

    @property
    def goles_totales_local(self):
        if self.goles_local is None:
            return None
        return self.goles_local + (self.penales_local or 0)

    @property
    def goles_totales_visitante(self):
        if self.goles_visitante is None:
            return None
        return self.goles_visitante + (self.penales_visitante or 0)

    @property
    def resultado_str(self):
        if self.goles_local is None:
            return 'vs'
        base = f"{self.goles_local} - {self.goles_visitante}"
        if self.hubo_penales:
            return f"{base} (pen. {self.penales_local}-{self.penales_visitante})"
        return base

    def __str__(self):
        return f"{self.pais_local} vs {self.pais_visitante}"


class TorneoConfig(models.Model):
    """Singleton: tournament branding config editable from the admin panel."""
    nombre = models.CharField(max_length=120, default='Mi Polla')
    temporada = models.CharField(max_length=30, default='2026', help_text='Ej: 2026, Copa América 2024')
    logo = models.ImageField(upload_to='torneo/', null=True, blank=True,
                             help_text='Logo del torneo (recomendado: fondo transparente, PNG)')
    color_primario = models.CharField(max_length=7, default='#6366f1',
                                      help_text='Color principal en hex, ej: #6366f1')
    color_secundario = models.CharField(max_length=7, default='#10b981',
                                        help_text='Color secundario en hex')
    cuota = models.DecimalField(max_digits=8, decimal_places=2, default=100.00,
                                help_text='Cuota de inscripción por participante en Bs.')
    pozo_activo = models.BooleanField(default=True,
                                      help_text='Mostrar la página El Gran Pozo')
    qr_pago = models.ImageField(upload_to='torneo/', null=True, blank=True,
                                help_text='QR de pago (PNG/JPG) para la landing page')
    whatsapp_pago = models.CharField(max_length=20, default='59170512621',
                                     help_text='Número WhatsApp para enviar comprobante de pago')
    inscripciones_abiertas = models.BooleanField(default=True,
                                                  help_text='Si está desactivado, oculta el QR y la sección de pago en el landing')
    correo_apertura_enviado = models.BooleanField(default=False,
                                                   help_text='Si ya se envió el correo especial de apertura (jugadores, campeones y 1er partido)')

    class Meta:
        verbose_name = 'Configuración del torneo'
        verbose_name_plural = 'Configuración del torneo'

    def save(self, *args, **kwargs):
        self.pk = 1  # enforce singleton
        super().save(*args, **kwargs)

    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return f"{self.nombre} {self.temporada}"


class GolPartido(models.Model):
    """Goals scored by a player in a specific match."""
    jugador = models.ForeignKey(Jugador, on_delete=models.CASCADE, related_name='goles_anotados')
    partido = models.ForeignKey(Partido, on_delete=models.CASCADE, related_name='goles')
    cantidad = models.SmallIntegerField(default=1)

    class Meta:
        unique_together = ['jugador', 'partido']
        verbose_name = 'Gol en partido'
        verbose_name_plural = 'Goles en partidos'

    def recalcular_bonus_jugador(self):
        """Recalculate selection bonus per user for this player.
        RULE: only counts goals in matches where the user made a prediction.
        Own goals (cantidad < 0) never award bonus."""
        from django.db.models import Sum
        for seleccion in SeleccionJugador.objects.filter(jugador=self.jugador).select_related('usuario'):
            # Only count goals in matches where THIS user predicted
            pred_partidos = seleccion.usuario.pronosticos.values_list('partido_id', flat=True)
            total = GolPartido.objects.filter(
                jugador=self.jugador,
                cantidad__gt=0,
                partido_id__in=pred_partidos,
            ).aggregate(t=Sum('cantidad'))['t'] or 0
            seleccion.puntos_acumulados = total * PUNTOS_POR_GOL
            seleccion.save(update_fields=['puntos_acumulados'])

    def __str__(self):
        return f"{self.jugador} - {self.partido} ({self.cantidad} gol)"


class PerfilUsuario(models.Model):
    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil')
    campeon = models.ForeignKey(Pais, on_delete=models.SET_NULL, null=True, blank=True,
                                related_name='pronosticantes_campeon')
    puntos_campeon = models.SmallIntegerField(default=0)
    telefono = models.CharField(max_length=20, blank=True, help_text='Formato internacional: 591XXXXXXXX')
    recibir_correos = models.BooleanField(default=False,
                                          help_text='Recibir por correo los pronósticos de todos al cierre de cada partido (transparencia)')

    class Meta:
        verbose_name = 'Perfil'
        verbose_name_plural = 'Perfiles'

    @property
    def puntos_pronosticos(self):
        from django.db.models import Sum
        return self.usuario.pronosticos.aggregate(t=Sum('puntos'))['t'] or 0

    @property
    def puntos_jugadores(self):
        """Sum of goleador points — only from matches the user predicted."""
        from django.db.models import Sum
        return self.usuario.jugadores_seleccionados.aggregate(
            t=Sum('puntos_acumulados')
        )['t'] or 0

    def recalcular_puntos_jugadores(self):
        """Recalculate all goleador pts for this user respecting prediction rule."""
        from django.db.models import Sum
        pred_partidos = self.usuario.pronosticos.values_list('partido_id', flat=True)
        for sel in self.usuario.jugadores_seleccionados.all():
            total = GolPartido.objects.filter(
                jugador=sel.jugador,
                cantidad__gt=0,
                partido_id__in=pred_partidos,
            ).aggregate(t=Sum('cantidad'))['t'] or 0
            sel.puntos_acumulados = total * PUNTOS_POR_GOL
            sel.save(update_fields=['puntos_acumulados'])

    @property
    def puntos_totales(self):
        return self.puntos_pronosticos + self.puntos_campeon + self.puntos_jugadores

    def __str__(self):
        return f"Perfil de {self.usuario.username}"


class SeleccionJugador(models.Model):
    """A user's selection of up to MAX_JUGADORES_SELECCION players.
    Each goal scored by these players awards PUNTOS_POR_GOL points.
    Selection is locked once the first match of the tournament starts."""
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='jugadores_seleccionados')
    jugador = models.ForeignKey(Jugador, on_delete=models.CASCADE, related_name='selecciones')
    puntos_acumulados = models.SmallIntegerField(default=0)

    class Meta:
        unique_together = ['usuario', 'jugador']
        verbose_name = 'Jugador seleccionado'
        verbose_name_plural = 'Jugadores seleccionados'

    def save(self, *args, **kwargs):
        # Only allow writes if recalculating points (puntos_acumulados update only on existing records)
        # or if tournament hasn't started yet
        if self.pk is None and torneo_iniciado():
            from django.core.exceptions import ValidationError
            raise ValidationError('La selección de jugadores está cerrada: el torneo ya inició.')
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.usuario.username} → {self.jugador.nombre_completo}"


class Pronostico(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='pronosticos')
    partido = models.ForeignKey(Partido, on_delete=models.CASCADE, related_name='pronosticos')
    goles_local = models.SmallIntegerField()
    goles_visitante = models.SmallIntegerField()
    predice_penales = models.BooleanField(default=False)
    puntos = models.SmallIntegerField(default=0)
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['usuario', 'partido']
        verbose_name = 'Pronóstico'
        verbose_name_plural = 'Pronósticos'

    @staticmethod
    def _signo(gl, gv):
        if gl > gv:
            return 'L'
        if gl < gv:
            return 'V'
        return 'E'

    def save(self, *args, **kwargs):
        # Block new predictions after match has started; allow updates to points by system
        if not self.partido.abierto and self.pk is None:
            from django.core.exceptions import ValidationError
            raise ValidationError(
                f'El partido {self.partido} ya inició, no se pueden registrar pronósticos.'
            )
        super().save(*args, **kwargs)

    def calcular_desglose(self) -> dict:
        """
        Returns point breakdown matching the reference scoring:
        - ganador: 3 pts if correct winner or draw
        - resultado: +2 pts bonus if exact score (on top of ganador)
        - penales: +2 pts if correctly predicted penalties (knockout only)
        Total for exact = 5, correct winner = 3, wrong = 0.
        """
        p = self.partido
        if not p.jugado or p.goles_local is None:
            return {'ganador': 0, 'resultado': 0, 'penales': 0, 'total': 0}

        real_gl = p.goles_totales_local
        real_gv = p.goles_totales_visitante

        pts_ganador = 0
        pts_resultado = 0
        pts_penales = 0

        if self._signo(self.goles_local, self.goles_visitante) == self._signo(real_gl, real_gv):
            pts_ganador = 3

        if self.goles_local == real_gl and self.goles_visitante == real_gv:
            pts_resultado = 2

        if p.es_eliminatoria and self.predice_penales == p.hubo_penales:
            pts_penales = 2

        return {
            'ganador': pts_ganador,
            'resultado': pts_resultado,
            'penales': pts_penales,
            'total': pts_ganador + pts_resultado + pts_penales,
        }

    def calcular_puntos(self):
        return self.calcular_desglose()['total']

    def __str__(self):
        return f"{self.usuario.username}: {self.partido} ({self.goles_local}-{self.goles_visitante})"
