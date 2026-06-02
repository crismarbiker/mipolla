from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from polla import views as polla_views

urlpatterns = [
    path('django-admin/', admin.site.urls),
    path('login/', polla_views.custom_login, name='login'),
    path('logout/', polla_views.custom_logout, name='logout'),
    path('', include('polla.urls', namespace='polla')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
