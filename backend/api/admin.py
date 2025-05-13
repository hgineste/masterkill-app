from django.contrib import admin
from .models import Player, Gage, MasterkillEvent, Game, GamePlayerStats, RedeployEvent

class PlayerAdmin(admin.ModelAdmin):
    list_display = ('gamertag', 'created_at')
    search_fields = ('gamertag',)

class GageAdmin(admin.ModelAdmin):
    list_display = ('text', 'created_at')
    search_fields = ('text',)

class MasterkillEventAdmin(admin.ModelAdmin):
    list_display = ('name', 'status', 'creator_username', 'created_at', 'num_games_planned')
    list_filter = ('status', 'creator')
    search_fields = ('name', 'creator__username')
    filter_horizontal = ('participants',)

    @admin.display(description='Créateur', ordering='creator__username')
    def creator_username(self, obj):
        return obj.creator.username if obj.creator else None

class GameAdmin(admin.ModelAdmin):
    list_display = ('game_identifier', 'masterkill_event_name', 'status', 'start_time', 'end_time')
    list_filter = ('status', 'masterkill_event__name')
    search_fields = ('masterkill_event__name', 'game_number')
    ordering = ('masterkill_event__name', 'game_number')

    @admin.display(description='Partie', ordering='masterkill_event__name') # Corrigé pour trier sur le nom du MK
    def game_identifier(self, obj):
        return f"Partie {obj.game_number}"

    @admin.display(description='Masterkill Event', ordering='masterkill_event__name')
    def masterkill_event_name(self, obj):
        return obj.masterkill_event.name if obj.masterkill_event else None

class GamePlayerStatsAdmin(admin.ModelAdmin):
    list_display = ('player_gamertag', 'game_info_admin', 'kills', 'deaths', 'assists', 'score_in_game')
    list_filter = ('game__masterkill_event__name', 'player__gamertag', 'game__game_number')
    search_fields = ('player__gamertag', 'game__masterkill_event__name')
    ordering = ('game__masterkill_event__name', 'game__game_number', 'player__gamertag')

    @admin.display(description='Joueur', ordering='player__gamertag')
    def player_gamertag(self, obj):
        return obj.player.gamertag if obj.player else None

    @admin.display(description='Infos Partie', ordering='game__masterkill_event__name')
    def game_info_admin(self, obj):
        if obj.game and obj.game.masterkill_event:
            return f"MK: {obj.game.masterkill_event.name} - P{obj.game.game_number}"
        return "N/A"

class RedeployEventAdmin(admin.ModelAdmin):
    list_display = ('timestamp_display', 'game_info_admin', 'redeployer_player_gamertag', 'redeployed_player_gamertag')
    list_filter = ('game__masterkill_event__name', 'game__game_number', 'redeployer_player', 'redeployed_player')
    search_fields = ('redeployer_player__gamertag', 'redeployed_player__gamertag', 'game__masterkill_event__name')
    ordering = ('-timestamp',)

    @admin.display(description='Date/Heure', ordering='timestamp')
    def timestamp_display(self, obj):
        return obj.timestamp.strftime("%Y-%m-%d %H:%M:%S") if obj.timestamp else None
    
    @admin.display(description='Infos Partie', ordering='game__masterkill_event__name')
    def game_info_admin(self, obj):
        if obj.game and obj.game.masterkill_event:
            return f"MK: {obj.game.masterkill_event.name} - P{obj.game.game_number}"
        return "N/A"

    @admin.display(description='Redéployeur', ordering='redeployer_player__gamertag')
    def redeployer_player_gamertag(self, obj):
        return obj.redeployer_player.gamertag if obj.redeployer_player else None

    @admin.display(description='Redéployé', ordering='redeployed_player__gamertag')
    def redeployed_player_gamertag(self, obj):
        return obj.redeployed_player.gamertag if obj.redeployed_player else None

admin.site.register(Player, PlayerAdmin)
admin.site.register(Gage, GageAdmin)
admin.site.register(MasterkillEvent, MasterkillEventAdmin)
admin.site.register(Game, GameAdmin)
admin.site.register(GamePlayerStats, GamePlayerStatsAdmin)
admin.site.register(RedeployEvent, RedeployEventAdmin)