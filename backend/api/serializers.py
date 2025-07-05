from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Gage, MasterkillEvent, Player, Game, GamePlayerStats, RedeployEvent, ReviveEvent

class PlayerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Player # Ce serializer pourrait devenir obsolète si vous n'utilisez plus Player directement
        fields = ['id', 'gamertag']

class UserSerializer(serializers.ModelSerializer): # Utilisé pour creator_details et maintenant participants_details
    class Meta:
        model = User
        fields = ['id', 'username'] # username sera l'équivalent de gamertag

class GageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Gage
        fields = ['id', 'text', 'created_at']

class GameSerializer(serializers.ModelSerializer):
    kill_multiplier = serializers.FloatField(read_only=True)
    spawn_location = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    # NOUVEAU: Pour afficher le nom du chef d'escouade
    squad_leader_username = serializers.CharField(source='squad_leader.username', read_only=True, allow_null=True)
    has_auto_stats  = serializers.BooleanField(read_only=True)

    class Meta:
        model = Game
        fields = [
            'id', 'masterkill_event', 'game_number', 'status', 
            'start_time', 'end_time', 'kill_multiplier', 'spawn_location',
            'squad_leader', 'squad_leader_username', 'has_auto_stats' # Ajout de squad_leader (ID) et son username
        ]
        read_only_fields = [
            'id', 'masterkill_event', 'start_time', 'end_time', 
            'kill_multiplier', 'squad_leader_username', 'has_auto_stats' 
            # squad_leader (ID) peut être défini lors de la création/maj d'une partie
        ]

class MasterkillEventSerializer(serializers.ModelSerializer):
    # MODIFIÉ: Utiliser UserSerializer pour participants_details car participants pointe vers User
    participants_details = UserSerializer(source='participants', many=True, read_only=True)
    creator_details = UserSerializer(source='creator', read_only=True, allow_null=True)
    selected_gage_text = serializers.CharField(source='selected_gage.text', read_only=True, allow_null=True)
    # MODIFIÉ: Utiliser UserSerializer pour winner_details car winner pointe vers User
    winner_details = UserSerializer(source='winner', read_only=True, allow_null=True)
    
    participant_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True, 
        required=False,
        allow_empty=True
    )
    custom_gage_input_text = serializers.CharField(
        write_only=True, required=False, allow_blank=True, allow_null=True
    )
    
    has_bonus_reel = serializers.BooleanField(required=False, default=True)
    has_kill_multipliers = serializers.BooleanField(required=False, default=False)

    current_game_info = serializers.SerializerMethodField(read_only=True)
    games = GameSerializer(many=True, read_only=True)
    completed_games_count = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = MasterkillEvent
        fields = [
            'id', 'name', 'creator', 'creator_details', 'created_at',
            'effective_start_at', 'ended_at',
            'points_kill', 'points_rea', 'points_redeploiement', 'points_goulag_win',
            'points_rage_quit', 'points_execution', 'points_humiliation',
            'num_games_planned', 'top1_solo_ends_mk',
            'selected_gage', 'selected_gage_text', 'custom_gage_input_text',
            'has_bonus_reel', 'has_kill_multipliers',
            'status', 'winner', 'winner_details',
            'participants', 'participants_details', 
            'participant_ids', 
            'current_game_info', 'games', 'completed_games_count'
        ]
        read_only_fields = [
            'creator', 
            'creator_details', 
            'participants_details',
            'selected_gage_text', 
            'winner_details',
            'current_game_info', 
            'games', 
            'completed_games_count',
        ]

    def get_completed_games_count(self, obj):
        if hasattr(obj, 'games'):
            return obj.games.filter(status='completed').count()
        return 0

    def get_current_game_info(self, obj):
        # Le GameSerializer utilisé ici remontera maintenant squad_leader_username
        current_inprogress_game = obj.games.filter(status='inprogress').order_by('game_number').first()
        if current_inprogress_game:
            return GameSerializer(current_inprogress_game).data
        
        next_pending_game = obj.games.filter(status='pending').order_by('game_number').first()
        if next_pending_game:
            return GameSerializer(next_pending_game).data
        
        if obj.status == 'pending' and not Game.objects.filter(masterkill_event_id=obj.id).exists():
            # Pour un MK pending sans partie, current_game_info peut inclure des valeurs par défaut
            return {'game_number': 1, 'status': 'pending', 'id': None, 'masterkill_event': obj.id, 'kill_multiplier': 1.0, 'spawn_location': None, 'squad_leader': None, 'squad_leader_username': None}
        return None

    def _handle_participants(self, instance, participant_ids):
        if participant_ids is not None:
            # CORRIGÉ: Filtrer sur User au lieu de Player
            valid_users = User.objects.filter(id__in=participant_ids)
            # Vous pouvez ajouter une validation ici pour vérifier si tous les IDs fournis sont valides
            # if len(valid_users) != len(set(participant_ids)):
            #     raise serializers.ValidationError("Un ou plusieurs IDs de participants sont invalides.")
            instance.participants.set(valid_users)
        elif participant_ids == []: # Si une liste vide est explicitement envoyée
             instance.participants.clear()


    def _handle_gage(self, instance, custom_gage_input_text):
        if custom_gage_input_text and custom_gage_input_text.strip():
            gage_obj, _ = Gage.objects.get_or_create(
                text__iexact=custom_gage_input_text.strip(), 
                defaults={'text': custom_gage_input_text.strip()}
            )
            instance.selected_gage = gage_obj
        elif 'custom_gage_input_text' in self.initial_data and custom_gage_input_text is None : 
            instance.selected_gage = None


    def create(self, validated_data):
        participant_ids = validated_data.pop('participant_ids', [])
        custom_gage_input_text = validated_data.pop('custom_gage_input_text', None)
        
        instance = super().create(validated_data)
        
        self._handle_participants(instance, participant_ids)
        
        if 'custom_gage_input_text' in self.initial_data:
            self._handle_gage(instance, custom_gage_input_text)
            instance.save()
        return instance

    def update(self, instance, validated_data):
        participant_ids = validated_data.pop('participant_ids', None)
        custom_gage_input_text = validated_data.pop('custom_gage_input_text', None)

        instance = super().update(instance, validated_data)

        if participant_ids is not None:
            self._handle_participants(instance, participant_ids)
        
        if 'custom_gage_input_text' in self.initial_data:
            self._handle_gage(instance, custom_gage_input_text)
            instance.save() 
            
        return instance

class RedeployEventSerializer(serializers.ModelSerializer):
    # CORRIGÉ: source pour utiliser username du modèle User
    redeployer_player_username = serializers.CharField(source='redeployer_player.username', read_only=True)
    redeployed_player_username = serializers.CharField(source='redeployed_player.username', read_only=True)
    game = serializers.PrimaryKeyRelatedField(queryset=Game.objects.all())
    redeployer_player = serializers.PrimaryKeyRelatedField(queryset=User.objects.all()) # CORRIGÉ: User
    redeployed_player = serializers.PrimaryKeyRelatedField(queryset=User.objects.all()) # CORRIGÉ: User

    class Meta:
        model = RedeployEvent
        fields = [
            'id', 'game',
            'redeployer_player', 'redeployer_player_username',
            'redeployed_player', 'redeployed_player_username',
            'timestamp'
        ]
        read_only_fields = ['id', 'timestamp', 'redeployer_player_username', 'redeployed_player_username']

class ReviveEventSerializer(serializers.ModelSerializer):
    # CORRIGÉ: source pour utiliser username du modèle User
    reviver_player_username = serializers.CharField(source='reviver_player.username', read_only=True)
    revived_player_username = serializers.CharField(source='revived_player.username', read_only=True)
    game = serializers.PrimaryKeyRelatedField(queryset=Game.objects.all())
    reviver_player = serializers.PrimaryKeyRelatedField(queryset=User.objects.all()) # CORRIGÉ: User
    revived_player = serializers.PrimaryKeyRelatedField(queryset=User.objects.all()) # CORRIGÉ: User

    class Meta:
        model = ReviveEvent
        fields = [
            'id', 'game', 
            'reviver_player', 'reviver_player_username', 
            'revived_player', 'revived_player_username', 
            'timestamp'
        ]
        read_only_fields = ['id', 'timestamp', 'reviver_player_username', 'revived_player_username']

class GamePlayerStatsSerializer(serializers.ModelSerializer):
    # CORRIGÉ: queryset pointe vers User
    player = serializers.PrimaryKeyRelatedField(queryset=User.objects.all()) 
    player_username = serializers.CharField(source='player.username', read_only=True) # Pour afficher le nom

    class Meta:
        model = GamePlayerStats
        fields = [
            'id', 'game', 'player', 'player_username',
            'kills', 'deaths', 'assists', 'gulag_status',
            'revives_done', 'times_executed_enemy', 'times_got_executed',
            'rage_quit', 'times_redeployed_by_teammate', 'score_in_game'
        ]
        read_only_fields = ['id', 'game', 'score_in_game', 'player_username']

class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})
    password_confirm = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'}, label="Confirm password")

    class Meta:
        model = User
        fields = ('username', 'password', 'password_confirm')

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({"password": "Les mots de passe ne correspondent pas."})
        if User.objects.filter(username=attrs['username']).exists():
             raise serializers.ValidationError({"username": "Ce nom d'utilisateur est déjà utilisé."})
        return attrs

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        user = User.objects.create_user(
            username=validated_data['username'],
            password=validated_data['password']
        )
        return user
    
class AggregatedPlayerStatsSerializer(serializers.Serializer):
    # CORRIGÉ: player devrait maintenant être UserSerializer si on veut les détails de l'User
    player = UserSerializer(read_only=True) # Au lieu de PlayerSerializer
    total_kills = serializers.IntegerField(default=0)
    total_deaths = serializers.IntegerField(default=0)
    total_assists = serializers.IntegerField(default=0)
    total_gulag_wins = serializers.IntegerField(default=0)
    total_gulag_lost = serializers.IntegerField(default=0)
    total_revives_done = serializers.IntegerField(default=0) # Sera basé sur ReviveEvents
    total_times_executed_enemy = serializers.IntegerField(default=0)
    total_times_got_executed = serializers.IntegerField(default=0)
    total_rage_quits = serializers.IntegerField(default=0)
    total_times_redeployed_by_teammate = serializers.IntegerField(default=0)
    total_score_from_games = serializers.IntegerField(default=0)
    games_played_in_mk = serializers.IntegerField(default=0)
    
class AllTimePlayerStatsSerializer(serializers.Serializer):
    # CORRIGÉ: player_id et gamertag devraient se référer à User.id et User.username
    player_id = serializers.IntegerField(source='id') # En supposant que la source est un objet User
    username = serializers.CharField(source='username') # Anciennement gamertag
    total_score = serializers.IntegerField()
    total_kills = serializers.IntegerField()
    total_deaths = serializers.IntegerField()
    total_assists = serializers.IntegerField()
    total_revives_done = serializers.IntegerField() # Sera basé sur ReviveEvents
    total_gulag_wins = serializers.IntegerField()
    total_rage_quits = serializers.IntegerField()
    total_times_redeployed = serializers.IntegerField()
    games_played = serializers.IntegerField()
    mks_won = serializers.IntegerField()
    kd_ratio = serializers.FloatField()