from django.contrib import admin
from .models import Player, Gage, MasterkillEvent # Importez vos modèles

# Enregistrez vos modèles ici pour qu'ils apparaissent dans l'admin
admin.site.register(Player)
admin.site.register(Gage)
admin.site.register(MasterkillEvent)