from django.db import models
from django.contrib.auth.models import User
import random

class Player(models.Model):
    gamertag = models.CharField(max_length=100, unique=True, verbose_name="Pseudo du joueur")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Date de création")

    def __str__(self):
        return self.gamertag

    class Meta:
        verbose_name = "Joueur"
        verbose_name_plural = "Joueurs"
        ordering = ['gamertag']

class Gage(models.Model):
    text = models.CharField(max_length=255, unique=True, verbose_name="Texte du gage")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Date de création")

    def __str__(self):
        return self.text

    class Meta:
        verbose_name = "Gage"
        verbose_name_plural = "Gages"
        ordering = ['text']

class MasterkillEvent(models.Model):
    name = models.CharField(max_length=150, default="Nouveau Masterkill", verbose_name="Nom du Masterkill")
    creator = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="created_masterkills", verbose_name="Créateur")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Date de création")
    effective_start_at = models.DateTimeField(null=True, blank=True, verbose_name="Début effectif")
    ended_at = models.DateTimeField(null=True, blank=True, verbose_name="Fin")
    
    points_kill = models.IntegerField(default=1, verbose_name="Points par Kill")
    points_rea = models.IntegerField(default=1, verbose_name="Points par Réanimation")
    points_redeploiement = models.IntegerField(default=-1, verbose_name="Points par Redéploiement")
    points_goulag_win = models.IntegerField(default=1, verbose_name="Points par Goulag gagné")
    points_rage_quit = models.IntegerField(default=-5, verbose_name="Points par Rage Quit")
    points_execution = models.IntegerField(default=1, verbose_name="Points par Exécution")
    points_humiliation = models.IntegerField(default=-1, verbose_name="Points par Humiliation subie")
    
    num_games_planned = models.PositiveIntegerField(default=3, verbose_name="Nombre de parties prévues")
    top1_solo_ends_mk = models.BooleanField(default=False, help_text="Un Top 1 solo met fin au MK ?", verbose_name="Top 1 Solo termine le MK")
    selected_gage = models.ForeignKey(Gage, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Gage sélectionné")
    
    has_bonus_reel = models.BooleanField(default=True, verbose_name="Roue des Bonus activée")
    has_kill_multipliers = models.BooleanField(default=False, verbose_name="Multiplicateurs de Kills activés")

    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('inprogress', 'En cours'),
        ('paused', 'En Pause'),
        ('completed', 'Terminé'),
        ('cancelled', 'Annulé'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="Statut")
    
    participants = models.ManyToManyField(Player, related_name="masterkill_events_participated", blank=True, verbose_name="Participants")
    winner = models.ForeignKey(Player, on_delete=models.SET_NULL, null=True, blank=True, related_name="masterkills_won", verbose_name="Vainqueur")

    def __str__(self):
        return f"MK: {self.name} ({self.get_status_display()})"

    class Meta:
        verbose_name = "Événement Masterkill"
        verbose_name_plural = "Événements Masterkill"
        ordering = ['-created_at']

class Game(models.Model):
    masterkill_event = models.ForeignKey(MasterkillEvent, related_name='games', on_delete=models.CASCADE, verbose_name="Événement Masterkill")
    game_number = models.PositiveIntegerField(verbose_name="Numéro de la partie")
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('inprogress', 'En cours'),
        ('completed', 'Terminée'),
    ]
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='pending', verbose_name="Statut de la partie")
    start_time = models.DateTimeField(null=True, blank=True, verbose_name="Début de la partie")
    end_time = models.DateTimeField(null=True, blank=True, verbose_name="Fin de la partie")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    kill_multiplier = models.FloatField(default=1.0, verbose_name="Multiplicateur de Kills")
    spawn_location = models.CharField(max_length=100, null=True, blank=True, verbose_name="Lieu de Spawn")

    class Meta:
        verbose_name = "Partie"
        verbose_name_plural = "Parties"
        unique_together = ['masterkill_event', 'game_number']
        ordering = ['masterkill_event', 'game_number']

    def __str__(self):
        mk_name = self.masterkill_event.name if self.masterkill_event else 'MK Inconnu'
        spawn_info = f" (Spawn: {self.spawn_location})" if self.spawn_location else ""
        return f"MK \"{mk_name}\" - Partie {self.game_number}{spawn_info} ({self.get_status_display()})"

    def determine_and_set_kill_multiplier(self):
        if self.masterkill_event.has_kill_multipliers:
            if random.random() < 0.10:
                self.kill_multiplier = random.choice([1.0, 1.5, 2.0, 2.5])
            else:
                self.kill_multiplier = 1.0
        else:
            self.kill_multiplier = 1.0

class GamePlayerStats(models.Model):
    game = models.ForeignKey(Game, related_name='player_stats', on_delete=models.CASCADE, verbose_name="Partie")
    player = models.ForeignKey(Player, related_name='game_stats', on_delete=models.CASCADE, verbose_name="Joueur")
    kills = models.PositiveIntegerField(default=0, verbose_name="Kills")
    deaths = models.PositiveIntegerField(default=0, verbose_name="Morts")
    assists = models.PositiveIntegerField(default=0, verbose_name="Assistances")
    revives_done = models.PositiveIntegerField(default=0, verbose_name="Réanimations effectuées")
    GULAG_CHOICES = [
        ('not_played', 'Fermeture'),
        ('won', 'Gagné'),
        ('lost', 'Perdu'),
    ]
    gulag_status = models.CharField(
        max_length=10, 
        choices=GULAG_CHOICES, 
        default='not_played', 
        verbose_name="Résultat Goulag"
    )
    times_executed_enemy = models.PositiveIntegerField(default=0, verbose_name="Exécutions sur ennemi")
    times_got_executed = models.PositiveIntegerField(default=0, verbose_name="Exécutions subies")
    rage_quit = models.BooleanField(default=False, verbose_name="A quitté en cours (Rage Quit)")
    times_redeployed_by_teammate = models.PositiveIntegerField(default=0, verbose_name="Redéployé par coéquipier")
    score_in_game = models.IntegerField(default=0, verbose_name="Score pour cette partie")

    class Meta:
        verbose_name = "Statistique Joueur par Partie"
        verbose_name_plural = "Statistiques Joueurs par Partie"
        unique_together = ['game', 'player']

    def __str__(self):
        player_gamertag = self.player.gamertag if self.player else 'Joueur Inconnu'
        game_info = 'Partie Inconnue'
        if self.game:
            mk_name = self.game.masterkill_event.name if self.game.masterkill_event else 'MK Inconnu'
            game_info = f"Partie {self.game.game_number} (MK \"{mk_name}\")"
        return f"{player_gamertag} dans {game_info}"

class RedeployEvent(models.Model):
    game = models.ForeignKey(Game, related_name='redeploy_events', on_delete=models.CASCADE, verbose_name="Partie Concernée")
    redeployer_player = models.ForeignKey(Player, related_name='initiated_redeploys', on_delete=models.CASCADE, verbose_name="Joueur qui redéploie")
    redeployed_player = models.ForeignKey(Player, related_name='was_redeployed_by_log', on_delete=models.CASCADE, verbose_name="Joueur redéployé")
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name="Horodatage")

    class Meta:
        verbose_name = "Événement de Redéploiement"
        verbose_name_plural = "Événements de Redéploiement"
        ordering = ['-timestamp']

    def __str__(self):
        redeployer_name = self.redeployer_player.gamertag if self.redeployer_player else 'N/A'
        redeployed_name = self.redeployed_player.gamertag if self.redeployed_player else 'N/A'
        game_info = f"Partie {self.game.game_number}" if self.game else "Partie Inconnue"
        mk_info = f"(MK {self.game.masterkill_event.name})" if self.game and self.game.masterkill_event else ""
        return f"{redeployer_name} a redéployé {redeployed_name} dans {game_info} {mk_info}"

class ReviveEvent(models.Model):
    game = models.ForeignKey(Game, related_name='revive_events', on_delete=models.CASCADE, verbose_name="Partie Concernée")
    reviver_player = models.ForeignKey(Player, related_name='revives_performed', on_delete=models.CASCADE, verbose_name="Joueur qui réanime")
    revived_player = models.ForeignKey(Player, related_name='was_revived_events', on_delete=models.CASCADE, verbose_name="Joueur réanimé")
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name="Horodatage")

    class Meta:
        verbose_name = "Événement de Réanimation"
        verbose_name_plural = "Événements de Réanimation"
        ordering = ['-timestamp']

    def __str__(self):
        reviver_name = self.reviver_player.gamertag if self.reviver_player else 'N/A'
        revived_name = self.revived_player.gamertag if self.revived_player else 'N/A'
        game_info = f"Partie {self.game.game_number}" if self.game else "Partie Inconnue"
        mk_info = f"(MK {self.game.masterkill_event.name})" if self.game and self.game.masterkill_event else ""
        return f"{reviver_name} a réanimé {revived_name} dans {game_info} {mk_info}"