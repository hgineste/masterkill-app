from django.db import models
from django.contrib.auth.models import User # Pour lier certains éléments aux utilisateurs Django

class Player(models.Model):
    gamertag = models.CharField(max_length=100, unique=True, verbose_name="Pseudo du joueur")
    # Si vous voulez lier un joueur à un compte utilisateur Django (optionnel pour l'instant)
    # user_account = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="player_profile")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Date de création")

    def __str__(self):
        return self.gamertag

    class Meta:
        verbose_name = "Joueur"
        verbose_name_plural = "Joueurs"

class Gage(models.Model):
    text = models.CharField(max_length=255, unique=True, verbose_name="Texte du gage")
    # Pourrait être utile de savoir si le gage a été ajouté par un admin ou un utilisateur plus tard
    # is_custom = models.BooleanField(default=False, verbose_name="Gage personnalisé")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Date de création")

    def __str__(self):
        return self.text

    class Meta:
        verbose_name = "Gage"
        verbose_name_plural = "Gages"

class MasterkillEvent(models.Model):
    name = models.CharField(max_length=150, default="Nouveau Masterkill", verbose_name="Nom du Masterkill")
    # L'utilisateur Django qui a créé cet événement MK
    creator = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="created_masterkills", verbose_name="Créateur")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Date de création")
    effective_start_at = models.DateTimeField(null=True, blank=True, verbose_name="Début effectif")
    ended_at = models.DateTimeField(null=True, blank=True, verbose_name="Fin")

    # --- Paramètres du Masterkill ---
    points_kill = models.IntegerField(default=1, verbose_name="Points par Kill")
    points_rea = models.IntegerField(default=1, verbose_name="Points par Réanimation")
    points_redeploiement = models.IntegerField(default=-1, verbose_name="Points par Redéploiement utilisé")
    points_goulag_win = models.IntegerField(default=1, verbose_name="Points par Goulag gagné")
    points_rage_quit = models.IntegerField(default=-5, verbose_name="Points par Rage Quit")
    points_execution = models.IntegerField(default=1, verbose_name="Points par Exécution")
    points_humiliation = models.IntegerField(default=-1, verbose_name="Points par Humiliation subie")

    num_games_planned = models.PositiveIntegerField(default=3, verbose_name="Nombre de parties prévues")
    top1_solo_ends_mk = models.BooleanField(default=False, help_text="Un Top 1 solo met-il fin au Masterkill ?", verbose_name="Top 1 Solo termine le MK")
    selected_gage = models.ForeignKey(Gage, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Gage sélectionné")

    STATUS_CHOICES = [
        ('pending', 'En attente de démarrage'),
        ('inprogress', 'En cours'),
        ('completed', 'Terminé'),
        ('cancelled', 'Annulé'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="Statut")

    # --- Participants et Vainqueur ---
    # Les joueurs qui participent à cet événement MK.
    # Un joueur peut participer à plusieurs MK, et un MK a plusieurs joueurs.
    participants = models.ManyToManyField(Player, related_name="masterkill_events_participated", blank=True, verbose_name="Participants")
    winner = models.ForeignKey(Player, on_delete=models.SET_NULL, null=True, blank=True, related_name="masterkills_won", verbose_name="Vainqueur")

    def __str__(self):
        return f"MK: {self.name} (Statut: {self.get_status_display()})" # get_status_display() est sympa pour afficher la valeur lisible du choix

    class Meta:
        verbose_name = "Événement Masterkill"
        verbose_name_plural = "Événements Masterkill"
        ordering = ['-created_at'] # Ordonner par date de création, du plus récent au plus ancien