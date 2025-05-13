from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Gage, MasterkillEvent, Player, Game, GamePlayerStats, RedeployEvent

class PlayerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Player
        fields = ['id', 'gamertag']

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username']

class GageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Gage
        fields = ['id', 'text', 'created_at']

class GameSerializer(serializers.ModelSerializer):
    class Meta:
        model = Game
        fields = ['id', 'masterkill_event', 'game_number', 'status', 'start_time', 'end_time']
        read_only_fields = ['id', 'masterkill_event', 'start_time', 'end_time']

class MasterkillEventSerializer(serializers.ModelSerializer):
    participants_details = PlayerSerializer(source='participants', many=True, read_only=True)
    creator_details = UserSerializer(source='creator', read_only=True, allow_null=True)
    selected_gage_text = serializers.CharField(source='selected_gage.text', read_only=True, allow_null=True)
    winner_details = PlayerSerializer(source='winner', read_only=True, allow_null=True)
    
    participant_gamertags = serializers.ListField(
        child=serializers.CharField(max_length=100, allow_blank=False), # Ne pas permettre de gamertag vide
        write_only=True, required=False, allow_empty=True 
    )
    custom_gage_input_text = serializers.CharField(
        write_only=True, required=False, allow_blank=True, allow_null=True
    )

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
            'status', 'winner', 'winner_details',
            'participants', 'participants_details', 'participant_gamertags',
            'current_game_info', 'games', 'completed_games_count'
        ]
        read_only_fields = [
            'creator', # Important: Le créateur est défini par la vue (request.user)
            'creator_details', 
            'participants_details',
            'selected_gage_text', 
            'winner_details',
            'current_game_info', 
            'games', 
            'completed_games_count',
            # 'status', 'winner', 'effective_start_at', 'ended_at' sont aussi souvent read_only
            # et gérés par la logique applicative plutôt que par le client directement.
        ]

    def get_completed_games_count(self, obj):
        if hasattr(obj, 'games'):
            return obj.games.filter(status='completed').count()
        return 0

    def get_current_game_info(self, obj):
        current_inprogress_game = obj.games.filter(status='inprogress').order_by('game_number').first()
        if current_inprogress_game:
            return GameSerializer(current_inprogress_game).data
        
        next_pending_game = obj.games.filter(status='pending').order_by('game_number').first()
        if next_pending_game:
            return GameSerializer(next_pending_game).data
        
        # Utiliser obj.id pour filtrer les jeux est plus direct si obj est une instance sauvegardée
        if obj.status == 'pending' and not Game.objects.filter(masterkill_event_id=obj.id).exists():
            return {'game_number': 1, 'status': 'pending', 'id': None, 'masterkill_event': obj.id}
        return None

    def _handle_participants(self, instance, participant_gamertags):
        if participant_gamertags is not None:
            instance.participants.clear() 
            for gamertag in participant_gamertags:
                if gamertag and gamertag.strip():
                    player, _ = Player.objects.get_or_create(gamertag=gamertag.strip())
                    instance.participants.add(player)

    def _handle_gage(self, instance, custom_gage_input_text):
        if custom_gage_input_text and custom_gage_input_text.strip():
            gage_obj, _ = Gage.objects.get_or_create(
                text__iexact=custom_gage_input_text.strip(),
                defaults={'text': custom_gage_input_text.strip()}
            )
            instance.selected_gage = gage_obj
        elif custom_gage_input_text is not None: # Si la clé est présente et la valeur est vide/null
            instance.selected_gage = None


    def create(self, validated_data):
        participant_gamertags = validated_data.pop('participant_gamertags', [])
        custom_gage_input_text = validated_data.pop('custom_gage_input_text', None)
        
        # 'creator' est déjà dans validated_data car il a été ajouté par la vue via serializer.save(creator=request.user)
        # avant d'appeler super().create() ou .create() de ce serializer.
        instance = MasterkillEvent.objects.create(**validated_data)
        
        self._handle_participants(instance, participant_gamertags)
        self._handle_gage(instance, custom_gage_input_text) # Appeler après la création de l'instance principale
        
        instance.save() # Sauvegarder les modifications de selected_gage
        return instance

    def update(self, instance, validated_data):
        participant_gamertags = validated_data.pop('participant_gamertags', None)
        custom_gage_input_text = validated_data.pop('custom_gage_input_text', None)

        # 'creator' ne devrait pas être dans validated_data pour un update, ou devrait être ignoré.
        # super().update() s'occupe des champs simples.
        instance = super().update(instance, validated_data)

        if participant_gamertags is not None:
            self._handle_participants(instance, participant_gamertags)
        
        # Gérer le gage seulement si la clé a été explicitement envoyée dans la requête.
        if 'custom_gage_input_text' in self.initial_data:
            self._handle_gage(instance, custom_gage_input_text)
        
        instance.save() # Sauvegarder les modifications (notamment pour selected_gage)
        return instance

class RedeployEventSerializer(serializers.ModelSerializer):
    redeployer_player_gamertag = serializers.CharField(source='redeployer_player.gamertag', read_only=True)
    redeployed_player_gamertag = serializers.CharField(source='redeployed_player.gamertag', read_only=True)
    game = serializers.PrimaryKeyRelatedField(queryset=Game.objects.all())
    redeployer_player = serializers.PrimaryKeyRelatedField(queryset=Player.objects.all())
    redeployed_player = serializers.PrimaryKeyRelatedField(queryset=Player.objects.all())

    class Meta:
        model = RedeployEvent
        fields = [
            'id', 'game',
            'redeployer_player', 'redeployer_player_gamertag',
            'redeployed_player', 'redeployed_player_gamertag',
            'timestamp'
        ]
        read_only_fields = ['id', 'timestamp', 'redeployer_player_gamertag', 'redeployed_player_gamertag']

class GamePlayerStatsSerializer(serializers.ModelSerializer):
    player = serializers.PrimaryKeyRelatedField(queryset=Player.objects.all())
    
    class Meta:
        model = GamePlayerStats
        fields = [
            'id', 'game', 'player',
            'kills', 'deaths', 'assists', 'gulag_status',
            'revives_done', 'times_executed_enemy', 'times_got_executed',
            'rage_quit', 'times_redeployed_by_teammate', 'score_in_game'
        ]
        read_only_fields = ['id', 'game', 'score_in_game']

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
        validated_data.pop('password_confirm') # On ne le stocke pas
        
        user = User.objects.create_user(
            username=validated_data['username'],
            password=validated_data['password']
        )

        return user
    
class AggregatedPlayerStatsSerializer(serializers.Serializer):
    player = PlayerSerializer(read_only=True)
    total_kills = serializers.IntegerField(default=0)
    total_deaths = serializers.IntegerField(default=0)
    total_assists = serializers.IntegerField(default=0)
    total_gulag_wins = serializers.IntegerField(default=0)
    total_revives_done = serializers.IntegerField(default=0)
    total_times_executed_enemy = serializers.IntegerField(default=0)
    total_times_got_executed = serializers.IntegerField(default=0)
    total_rage_quits = serializers.IntegerField(default=0)
    total_times_redeployed_by_teammate = serializers.IntegerField(default=0)
    total_score_from_games = serializers.IntegerField(default=0)
    
class AllTimePlayerStatsSerializer(serializers.Serializer):
    player_id = serializers.IntegerField()
    gamertag = serializers.CharField()
    total_score = serializers.IntegerField()
    total_kills = serializers.IntegerField()
    total_deaths = serializers.IntegerField()
    total_assists = serializers.IntegerField()
    total_revives_done = serializers.IntegerField()
    total_gulag_wins = serializers.IntegerField()
    total_rage_quits = serializers.IntegerField()
    total_times_redeployed = serializers.IntegerField()
    games_played = serializers.IntegerField()
    mks_won = serializers.IntegerField()
    kd_ratio = serializers.FloatField()