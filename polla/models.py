from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

LETRA_GRUPO = {1: 'A', 2: 'B', 3: 'C', 4: 'D', 5: 'E', 6: 'F',
               7: 'G', 8: 'H', 9: 'I', 10: 'J', 11: 'K', 12: 'L'}

MAX_JUGADORES_SELECCION = 5
PUNTOS_POR_GOL = 2


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
        from django.db.models import Sum
        return self.goles_anotados.aggregate(t=Sum('cantidad'))['t'] or 0

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
        """After saving, update points for all users who selected this player."""
        from django.db.models import Sum
        total = GolPartido.objects.filter(
            jugador=self.jugador
        ).aggregate(t=Sum('cantidad'))['t'] or 0
        SeleccionJugador.objects.filter(jugador=self.jugador).update(
            puntos_acumulados=total * PUNTOS_POR_GOL
        )

    def __str__(self):
        return f"{self.jugador} - {self.partido} ({self.cantidad} gol)"


class PerfilUsuario(models.Model):
    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil')
    campeon = models.ForeignKey(Pais, on_delete=models.SET_NULL, null=True, blank=True,
                                related_name='pronosticantes_campeon')
    puntos_campeon = models.SmallIntegerField(default=0)

    class Meta:
        verbose_name = 'Perfil'
        verbose_name_plural = 'Perfiles'

    @property
    def puntos_pronosticos(self):
        from django.db.models import Sum
        return self.usuario.pronosticos.aggregate(t=Sum('puntos'))['t'] or 0

    @property
    def puntos_jugadores(self):
        from django.db.models import Sum
        return self.usuario.jugadores_seleccionados.aggregate(
            t=Sum('puntos_acumulados')
        )['t'] or 0

    @property
    def puntos_totales(self):
        return self.puntos_pronosticos + self.puntos_campeon + self.puntos_jugadores

    def __str__(self):
        return f"Perfil de {self.usuario.username}"


class SeleccionJugador(models.Model):
    """A user's selection of up to MAX_JUGADORES_SELECCION players.
    Each goal scored by these players awards PUNTOS_POR_GOL points."""
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='jugadores_seleccionados')
    jugador = models.ForeignKey(Jugador, on_delete=models.CASCADE, related_name='selecciones')
    puntos_acumulados = models.SmallIntegerField(default=0)

    class Meta:
        unique_together = ['usuario', 'jugador']
        verbose_name = 'Jugador seleccionado'
        verbose_name_plural = 'Jugadores seleccionados'

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

    def calcular_puntos(self):
        p = self.partido
        if not p.jugado or p.goles_local is None:
            return 0

        puntos = 0
        real_gl = p.goles_totales_local
        real_gv = p.goles_totales_visitante

        if self.goles_local == real_gl and self.goles_visitante == real_gv:
            puntos += 3
        elif self._signo(self.goles_local, self.goles_visitante) == self._signo(real_gl, real_gv):
            puntos += 2  # Correct outcome (not exact score): +2 pts

        # Bonus penales (only knockout rounds): +2 if correctly predicted
        if p.es_eliminatoria:
            if self.predice_penales == p.hubo_penales:
                puntos += 2

        return puntos

    def __str__(self):
        return f"{self.usuario.username}: {self.partido} ({self.goles_local}-{self.goles_visitante})"
