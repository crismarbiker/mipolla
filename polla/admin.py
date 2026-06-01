from django.contrib import admin
from .models import Fase, Estadio, Pais, Jugador, Partido, Pronostico, PerfilUsuario, GolPartido


@admin.register(Fase)
class FaseAdmin(admin.ModelAdmin):
    list_display = ['id_fase', 'descripcion']


@admin.register(Estadio)
class EstadioAdmin(admin.ModelAdmin):
    list_display = ['id', 'nombre']
    search_fields = ['nombre']


@admin.register(Pais)
class PaisAdmin(admin.ModelAdmin):
    list_display = ['id', 'nombre', 'letra_grupo', 'es_campeon']
    list_filter = ['grupo', 'es_campeon']
    search_fields = ['nombre']


@admin.register(Jugador)
class JugadorAdmin(admin.ModelAdmin):
    list_display = ['nombre_completo', 'pais', 'edad']
    list_filter = ['pais__grupo', 'pais']
    search_fields = ['nombre_completo', 'pais__nombre']
    autocomplete_fields = ['pais']


@admin.register(Partido)
class PartidoAdmin(admin.ModelAdmin):
    list_display = ['id', 'pais_local', 'pais_visitante', 'fase', 'fecha', 'goles_local', 'goles_visitante', 'jugado']
    list_filter = ['fase', 'jugado']
    list_editable = ['goles_local', 'goles_visitante', 'jugado']
    autocomplete_fields = ['pais_local', 'pais_visitante']
    date_hierarchy = 'fecha'


@admin.register(Pronostico)
class PronosticoAdmin(admin.ModelAdmin):
    list_display = ['usuario', 'partido', 'goles_local', 'goles_visitante', 'puntos']
    list_filter = ['puntos', 'partido__fase']
    search_fields = ['usuario__username']
    readonly_fields = ['puntos', 'creado', 'actualizado']


@admin.register(PerfilUsuario)
class PerfilAdmin(admin.ModelAdmin):
    list_display = ['usuario', 'campeon', 'goleador', 'puntos_campeon', 'puntos_goleador']
    search_fields = ['usuario__username']


@admin.register(GolPartido)
class GolAdmin(admin.ModelAdmin):
    list_display = ['jugador', 'partido', 'cantidad']
    autocomplete_fields = ['jugador']
