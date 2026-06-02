from django.urls import path
from . import views

app_name = 'polla'

urlpatterns = [
    path('', views.home, name='home'),
    path('partidos/', views.partidos, name='partidos'),
    path('pronosticos/', views.pronosticos, name='pronosticos'),
    path('ranking/', views.ranking, name='ranking'),
    path('ranking/<str:username>/', views.pronosticos_usuario, name='pronosticos_usuario'),
    path('reglas/', views.reglas, name='reglas'),
    path('gran-pozo/', views.gran_pozo, name='gran_pozo'),
    path('admin/usuarios/', views.admin_usuarios, name='admin_usuarios'),
    path('admin/usuarios/<int:pk>/toggle/', views.admin_toggle_usuario, name='admin_toggle_usuario'),
    path('admin/usuarios/<int:pk>/reset-password/', views.admin_reset_password, name='admin_reset_password'),
    path('admin/resultados/', views.admin_resultados, name='admin_resultados'),
    path('admin/resultados/<int:pk>/fetch/', views.admin_fetch_resultado, name='admin_fetch_resultado'),
    path('admin/whatsapp/test/', views.admin_test_whatsapp, name='admin_test_whatsapp'),
    path('admin/whatsapp/registrar/', views.admin_registrar_webhook, name='admin_registrar_webhook'),
    path('admin/eliminatorias/', views.admin_generar_eliminatorias, name='admin_generar_eliminatorias'),
    path('webhook/whatsapp/', views.webhook_whatsapp, name='webhook_whatsapp'),
    path('forgot-password/', views.forgot_password, name='forgot_password'),
]
