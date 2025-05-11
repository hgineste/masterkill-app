"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include # Assurez-vous que 'include' est importé

urlpatterns = [
    path('admin/', admin.site.urls),
    # Pour la page de login/logout de l'API navigable de Django REST Framework
    path('api-auth/', include('rest_framework.urls')),
    # Pour inclure les URLs de votre application 'api'
    path('api/', include('api.urls')), 
]