from django.urls import path
from . import views

app_name = 'polla'

urlpatterns = [
    path('', views.home, name='home'),
    path('partidos/', views.partidos, name='partidos'),
    path('pronosticos/', views.pronosticos, name='pronosticos'),
    path('ranking/', views.ranking, name='ranking'),
    path('admin/usuarios/', views.admin_usuarios, name='admin_usuarios'),
    path('admin/usuarios/<int:pk>/toggle/', views.admin_toggle_usuario, name='admin_toggle_usuario'),
    path('admin/resultados/', views.admin_resultados, name='admin_resultados'),
    path('admin/resultados/<int:pk>/fetch/', views.admin_fetch_resultado, name='admin_fetch_resultado'),
]
