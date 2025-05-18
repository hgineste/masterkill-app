from django.contrib import admin
from .models import Player, Gage, MasterkillEvent, Game, GamePlayerStats, RedeployEvent, ReviveEvent

# Si vous n'utilisez plus le modèle Player, vous pouvez commenter ou supprimer PlayerAdmin et son enregistrement.
# Pour l'instant, je le laisse si vous l'utilisez ailleurs, mais les relations principales pointent vers User.
class PlayerAdmin(admin.ModelAdmin):
    list_display = ('gamertag', 'created_at')
    search_fields = ('gamertag',)

class GageAdmin(admin.ModelAdmin):
    list_display = ('text', 'created_at')
    search_fields = ('text',)

class MasterkillEventAdmin(admin.ModelAdmin):
    list_display = ('name', 'status', 'creator_username_display', 'created_at', 'num_games_planned', 'winner_username_display')
    list_filter = ('status', 'creator')
    search_fields = ('name', 'creator__username', 'participants__username')
    filter_horizontal = ('participants',) # Fonctionnera car participants pointe maintenant vers User

    @admin.display(description='Créateur', ordering='creator__username')
    def creator_username_display(self, obj):
        return obj.creator.username if obj.creator else None

    @admin.display(description='Vainqueur', ordering='winner__username')
    def winner_username_display(self, obj):
        return obj.winner.username if obj.winner else None

class GameAdmin(admin.ModelAdmin):
    list_display = ('game_identifier', 'masterkill_event_name', 'status', 'start_time', 'end_time', 'kill_multiplier', 'spawn_location')
    list_filter = ('status', 'masterkill_event__name')
    search_fields = ('masterkill_event__name', 'game_number', 'spawn_location')
    ordering = ('masterkill_event__name', 'game_number')

    @admin.display(description='Partie', ordering='game_number')
    def game_identifier(self, obj):
        return f"Partie {obj.game_number}"

    @admin.display(description='Masterkill Event', ordering='masterkill_event__name')
    def masterkill_event_name(self, obj):
        return obj.masterkill_event.name if obj.masterkill_event else None

class GamePlayerStatsAdmin(admin.ModelAdmin):
    list_display = ('player_username_display', 'game_info_admin', 'kills', 'deaths', 'assists', 'score_in_game')
    list_filter = ('game__masterkill_event__name', 'player__username', 'game__game_number')
    search_fields = ('player__username', 'game__masterkill_event__name')
    ordering = ('game__masterkill_event__name', 'game__game_number', 'player__username')

    @admin.display(description='Utilisateur (Joueur)', ordering='player__username')
    def player_username_display(self, obj):
        return obj.player.username if obj.player else None

    @admin.display(description='Infos Partie', ordering='game__masterkill_event__name')
    def game_info_admin(self, obj):
        if obj.game and obj.game.masterkill_event:
            return f"MK: {obj.game.masterkill_event.name} - P{obj.game.game_number}"
        return "N/A"

class RedeployEventAdmin(admin.ModelAdmin):
    list_display = ('timestamp_display', 'game_info_admin', 'redeployer_username_display', 'redeployed_username_display')
    list_filter = ('game__masterkill_event__name', 'game__game_number', 'redeployer_player__username', 'redeployed_player__username')
    search_fields = ('redeployer_player__username', 'redeployed_player__username', 'game__masterkill_event__name')
    ordering = ('-timestamp',)
    raw_id_fields = ('game', 'redeployer_player', 'redeployed_player')

    @admin.display(description='Date/Heure', ordering='timestamp')
    def timestamp_display(self, obj):
        return obj.timestamp.strftime("%Y-%m-%d %H:%M:%S") if obj.timestamp else None
    
    @admin.display(description='Infos Partie', ordering='game__masterkill_event__name')
    def game_info_admin(self, obj):
        if obj.game and obj.game.masterkill_event:
            return f"MK: {obj.game.masterkill_event.name} - P{obj.game.game_number}"
        return "N/A"

    @admin.display(description='Redéployeur', ordering='redeployer_player__username')
    def redeployer_username_display(self, obj):
        return obj.redeployer_player.username if obj.redeployer_player else None

    @admin.display(description='Redéployé', ordering='redeployed_player__username')
    def redeployed_username_display(self, obj):
        return obj.redeployed_player.username if obj.redeployed_player else None

class ReviveEventAdmin(admin.ModelAdmin):
    list_display = ('timestamp_display', 'game_info_admin', 'reviver_username_display', 'revived_username_display')
    list_filter = ('game__masterkill_event__name', 'game__game_number', 'reviver_player__username', 'revived_player__username')
    search_fields = ('reviver_player__username', 'revived_player__username', 'game__masterkill_event__name')
    ordering = ('-timestamp',)
    raw_id_fields = ('game', 'reviver_player', 'revived_player')

    @admin.display(description='Date/Heure', ordering='timestamp')
    def timestamp_display(self, obj):
        return obj.timestamp.strftime("%Y-%m-%d %H:%M:%S") if obj.timestamp else None
    
    @admin.display(description='Infos Partie', ordering='game__masterkill_event__name')
    def game_info_admin(self, obj):
        if obj.game and obj.game.masterkill_event:
            return f"MK: {obj.game.masterkill_event.name} - P{obj.game.game_number}"
        return "N/A"

    @admin.display(description='Réanimateur', ordering='reviver_player__username')
    def reviver_username_display(self, obj):
        return obj.reviver_player.username if obj.reviver_player else None

    @admin.display(description='Réanimé', ordering='revived_player__username')
    def revived_username_display(self, obj):
        return obj.revived_player.username if obj.revived_player else None

# Si vous décidez de ne plus utiliser le modèle Player, commentez ou supprimez la ligne suivante :
admin.site.register(Player, PlayerAdmin) 
admin.site.register(Gage, GageAdmin)
admin.site.register(MasterkillEvent, MasterkillEventAdmin)
admin.site.register(Game, GameAdmin)
admin.site.register(GamePlayerStats, GamePlayerStatsAdmin)
admin.site.register(RedeployEvent, RedeployEventAdmin)
admin.site.register(ReviveEvent, ReviveEventAdmin) # Enregistrement du nouveau modèle