from django.contrib import admin
from django.urls import path, include
from rest_framework.authtoken.views import obtain_auth_token

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api-auth/', include('rest_framework.urls')), # Pour le login/logout de l'API navigable DRF
    path('api/', include('api.urls')),                 # C'est la ligne qui inclut les URLs de votre app 'api'
    path('api/auth/login/', obtain_auth_token, name='api_token_auth'), # Pour obtenir un token
]