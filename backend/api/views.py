from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth.models import User
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.db.models import Sum, Count, Q, F, FloatField, Case, When
from rest_framework.permissions import IsAuthenticated
import random

from .models import Gage, MasterkillEvent, Player, Game, GamePlayerStats, RedeployEvent, ReviveEvent
from .serializers import (
    GageSerializer, MasterkillEventSerializer, PlayerSerializer,
    GameSerializer, RedeployEventSerializer, GamePlayerStatsSerializer,
    AggregatedPlayerStatsSerializer, AllTimePlayerStatsSerializer,
    UserRegistrationSerializer, UserSerializer, ReviveEventSerializer 
)

@api_view(['GET'])
def list_gages(request):
    gages = Gage.objects.all().order_by('text')
    serializer = GageSerializer(gages, many=True)
    return Response(serializer.data)

class UserRegistrationView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]

class CurrentUserView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)
    
class MasterkillAggregatedStatsView(APIView):
    permission_classes = [permissions.AllowAny]
    def get(self, request, pk=None):
        mk_event = get_object_or_404(MasterkillEvent, pk=pk)
        completed_games = mk_event.games.filter(status='completed')
        aggregated_stats_list = []
        for player in mk_event.participants.all():
            player_data_serialized = PlayerSerializer(player).data
            
            # Compter les réanimations effectuées à partir de ReviveEvent
            revives_done_count = ReviveEvent.objects.filter(
                game__in=completed_games, 
                reviver_player=player
            ).count()

            stats = GamePlayerStats.objects.filter(
                game__in=completed_games, player=player
            ).aggregate(
                total_kills=Sum('kills', default=0),
                total_deaths=Sum('deaths', default=0),
                total_assists=Sum('assists', default=0),
                total_gulag_wins=Count('gulag_status', filter=Q(gulag_status='won')),
                total_gulag_lost=Count('gulag_status', filter=Q(gulag_status='lost')),
                # total_revives_done=Sum('revives_done', default=0), # Remplacé par le comptage de ReviveEvent
                total_times_executed_enemy=Sum('times_executed_enemy', default=0),
                total_times_got_executed=Sum('times_got_executed', default=0),
                total_rage_quits=Count('rage_quit', filter=Q(rage_quit=True)),
                total_times_redeployed_by_teammate=Sum('times_redeployed_by_teammate', default=0),
                total_score_from_games=Sum('score_in_game', default=0),
                games_played_in_mk=Count('game', distinct=True)
            )
            player_aggregated_data = {
                'player': player_data_serialized,
                'total_kills': stats['total_kills'],
                'total_deaths': stats['total_deaths'],
                'total_assists': stats['total_assists'],
                'total_gulag_wins': stats['total_gulag_wins'],
                'total_gulag_lost': stats['total_gulag_lost'],
                'total_revives_done': revives_done_count, # Utilisation du comptage de ReviveEvent
                'total_times_executed_enemy': stats['total_times_executed_enemy'],
                'total_times_got_executed': stats['total_times_got_executed'],
                'total_rage_quits': stats['total_rage_quits'],
                'total_times_redeployed_by_teammate': stats['total_times_redeployed_by_teammate'],
                'total_score_from_games': stats['total_score_from_games'],
                'games_played_in_mk': stats['games_played_in_mk']
            }
            aggregated_stats_list.append(player_aggregated_data)
        serializer = AggregatedPlayerStatsSerializer(aggregated_stats_list, many=True)
        return Response(serializer.data)

class MasterkillEventListCreateView(generics.ListCreateAPIView):
    queryset = MasterkillEvent.objects.all().order_by('-created_at')
    serializer_class = MasterkillEventSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    
    def perform_create(self, serializer):
        serializer.save(creator=self.request.user)

class MasterkillEventRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = MasterkillEvent.objects.all()
    serializer_class = MasterkillEventSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

class ManageGameView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk=None):
        mk_event = get_object_or_404(MasterkillEvent, pk=pk)
        action_type = request.data.get('action')

        if action_type == 'start_next_game':
            if mk_event.status in ['completed', 'cancelled']:
                return Response({"error": "Ce MK est terminé ou annulé."}, status=status.HTTP_400_BAD_REQUEST)

            current_inprogress_game = mk_event.games.filter(status='inprogress').first()
            if current_inprogress_game:
                return Response(GameSerializer(current_inprogress_game).data, status=status.HTTP_200_OK)

            next_game_to_start = mk_event.games.filter(status='pending').order_by('game_number').first()

            if not next_game_to_start:
                last_completed_game_number = 0
                last_game = mk_event.games.order_by('-game_number').first()
                if last_game:
                    last_completed_game_number = last_game.game_number
                
                if last_completed_game_number >= mk_event.num_games_planned:
                    return Response({"error": "Toutes les parties prévues ont été jouées ou la prochaine n'est pas encore créée."}, status=status.HTTP_400_BAD_REQUEST)
                
                next_game_number = last_completed_game_number + 1
                next_game_to_start, created = Game.objects.get_or_create(
                    masterkill_event=mk_event,
                    game_number=next_game_number,
                    defaults={'status': 'pending'} 
                )
                if not created and next_game_to_start.status != 'pending':
                     return Response({"error": f"La partie {next_game_number} existe déjà avec un statut inattendu: {next_game_to_start.status}."}, status=status.HTTP_400_BAD_REQUEST)

            next_game_to_start.status = 'inprogress'
            next_game_to_start.start_time = timezone.now()
            
            next_game_to_start.determine_and_set_kill_multiplier()
            
            next_game_to_start.save()

            if mk_event.status == 'pending':
                mk_event.status = 'inprogress'
                if not mk_event.effective_start_at:
                    mk_event.effective_start_at = timezone.now()
                mk_event.save()
            
            return Response(GameSerializer(next_game_to_start).data, status=status.HTTP_200_OK)

        return Response({"error": "Action non reconnue dans manage_game."}, status=status.HTTP_400_BAD_REQUEST)

class RedeployEventCreateView(generics.CreateAPIView):
    queryset = RedeployEvent.objects.all()
    serializer_class = RedeployEventSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        redeploy_event = serializer.save()
        stats, _ = GamePlayerStats.objects.get_or_create(
            game=redeploy_event.game, 
            player=redeploy_event.redeployed_player,
            defaults={'game_id': redeploy_event.game.id, 'player_id': redeploy_event.redeployed_player.id}
        )
        stats.times_redeployed_by_teammate = (stats.times_redeployed_by_teammate or 0) + 1
        stats.save()

class ReviveEventCreateView(generics.CreateAPIView): # NOUVELLE VUE
    queryset = ReviveEvent.objects.all()
    serializer_class = ReviveEventSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        revive_event = serializer.save()
        # Mettre à jour le compteur revives_done sur GamePlayerStats pour le joueur qui a réanimé
        stats, _ = GamePlayerStats.objects.get_or_create(
            game=revive_event.game, 
            player=revive_event.reviver_player,
            defaults={'game_id': revive_event.game.id, 'player_id': revive_event.reviver_player.id}
        )
        stats.revives_done = (stats.revives_done or 0) + 1
        stats.save()
        # Vous pourriez aussi vouloir suivre 'times_revived' pour le joueur réanimé si vous ajoutez ce champ à GamePlayerStats

class EndGameAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, game_pk=None):
        game_instance = get_object_or_404(Game, pk=game_pk)
        mk_event = game_instance.masterkill_event

        if game_instance.status == 'completed':
            return Response({"message": "Cette partie est déjà terminée."}, status=status.HTTP_400_BAD_REQUEST)
        if mk_event.status != 'inprogress' and mk_event.status != 'paused':
            return Response({"error": "Le Masterkill n'est pas en cours ou en pause."}, status=status.HTTP_400_BAD_REQUEST)

        player_stats_data_list = request.data.get('player_stats', [])
        game_spawn_location = request.data.get('spawn_location', None) 

        if not isinstance(player_stats_data_list, list):
            return Response({"error": "Le champ 'player_stats' doit être une liste."}, status=status.HTTP_400_BAD_REQUEST)

        for player_data in player_stats_data_list:
            if not player_data: continue
            player_id = player_data.get('player_id')
            if not player_id: continue
            try:
                player_instance = Player.objects.get(pk=player_id)
            except Player.DoesNotExist:
                continue

            kills = int(player_data.get('kills', 0))
            deaths = int(player_data.get('deaths', 0))
            gulag_status = player_data.get('gulag_status', 'not_played')
            # revives_done n'est plus directement pris du payload pour le score,
            # mais on le garde pour GamePlayerStats si le frontend l'envoie encore.
            # Le score pour les réas sera basé sur les ReviveEvents.
            revives_done_from_payload = int(player_data.get('revives_done', 0))
            times_executed_enemy = int(player_data.get('times_executed_enemy', 0))
            times_got_executed = int(player_data.get('times_got_executed', 0))
            rage_quit = bool(player_data.get('rage_quit', False))
            times_redeployed_by_teammate = int(player_data.get('times_redeployed_by_teammate', 0))

            actual_revives_done_for_score = ReviveEvent.objects.filter(game=game_instance, reviver_player=player_instance).count()

            score = 0
            score += (kills * mk_event.points_kill * game_instance.kill_multiplier)
            score += actual_revives_done_for_score * mk_event.points_rea # Score basé sur ReviveEvent
            if gulag_status == 'won':
                score += mk_event.points_goulag_win
            score += times_redeployed_by_teammate * mk_event.points_redeploiement
            if rage_quit:
                score += mk_event.points_rage_quit
            score += times_executed_enemy * mk_event.points_execution
            score += times_got_executed * mk_event.points_humiliation
            
            stats_defaults = {
                'kills': kills, 'deaths': deaths, 'assists': player_data.get('assists', 0),
                'gulag_status': gulag_status, 
                'revives_done': revives_done_from_payload, # On stocke ce que le frontend envoie pour le compteur simple
                'times_executed_enemy': times_executed_enemy, 'times_got_executed': times_got_executed,
                'rage_quit': rage_quit, 'times_redeployed_by_teammate': times_redeployed_by_teammate,
                'score_in_game': score
            }
            GamePlayerStats.objects.update_or_create(
                game=game_instance, player=player_instance,
                defaults=stats_defaults
            )
        
        game_instance.status = 'completed'
        game_instance.end_time = timezone.now()
        if game_spawn_location and game_spawn_location.strip():
            game_instance.spawn_location = game_spawn_location.strip()
        game_instance.save()

        completed_games_count = mk_event.games.filter(status='completed').count()
        mk_status_updated_to_completed = False
        if completed_games_count >= mk_event.num_games_planned:
            mk_event.status = 'completed'
            mk_event.ended_at = timezone.now()
            mk_event.save()
            mk_status_updated_to_completed = True
            
        return Response({
            "message": f"Partie {game_instance.game_number} terminée.", "game_id": game_instance.id,
            "game_status": game_instance.status, "mk_status": mk_event.status,
            "mk_ended": mk_status_updated_to_completed
        }, status=status.HTTP_200_OK)

class AllTimePlayerRankingView(generics.ListAPIView):
    serializer_class = AllTimePlayerStatsSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        players_with_stats = Player.objects.filter(game_stats__game__status='completed').distinct()
        player_rankings = []
        for player in players_with_stats:
            # Pour total_revives_done, on va sommer les ReviveEvents où ce joueur est le reviver
            total_revives_done_by_player = ReviveEvent.objects.filter(
                game__status='completed', 
                reviver_player=player
            ).count()

            stats = GamePlayerStats.objects.filter(player=player, game__status='completed').aggregate(
                total_score=Sum('score_in_game', default=0),
                total_kills=Sum('kills', default=0),
                total_deaths=Sum('deaths', default=0),
                total_assists=Sum('assists', default=0),
                # total_revives_done=Sum('revives_done', default=0), # Remplacé
                total_gulag_wins=Count('gulag_status', filter=Q(gulag_status='won')),
                total_rage_quits=Count('rage_quit', filter=Q(rage_quit=True)),
                total_times_redeployed=Sum('times_redeployed_by_teammate', default=0),
                games_played=Count('game', distinct=True)
            )
            mks_won = MasterkillEvent.objects.filter(winner=player, status='completed').count()
            
            deaths_for_kd = stats['total_deaths'] if stats['total_deaths'] > 0 else 1
            kd_ratio = round((stats['total_kills'] or 0) / deaths_for_kd, 2)
            if stats['total_deaths'] == 0 and stats['total_kills'] > 0 : kd_ratio = stats['total_kills']

            player_data = {
                'player_id': player.id, 'gamertag': player.gamertag,
                'total_score': stats['total_score'], 'total_kills': stats['total_kills'],
                'total_deaths': stats['total_deaths'], 'total_assists': stats['total_assists'],
                'total_revives_done': total_revives_done_by_player, # Utilise le nouveau comptage
                'total_gulag_wins': stats['total_gulag_wins'],
                'total_rage_quits': stats['total_rage_quits'], 'total_times_redeployed': stats['total_times_redeployed'],
                'games_played': stats['games_played'], 'mks_won': mks_won, 'kd_ratio': kd_ratio
            }
            player_rankings.append(player_data)
        
        player_rankings.sort(key=lambda x: x['total_score'], reverse=True)
        return player_rankings

class MasterkillGameScoresView(APIView):
    permission_classes = [permissions.AllowAny]
    def get(self, request, pk=None):
        mk_event = get_object_or_404(MasterkillEvent, pk=pk)
        response_data = {
            'mk_id': mk_event.id, 'mk_name': mk_event.name, 
            'num_games_planned': mk_event.num_games_planned,
            'participants': PlayerSerializer(mk_event.participants.all(), many=True).data,
            'player_scores_per_game': {}
        }
        
        completed_games_instances = mk_event.games.filter(status='completed').order_by('game_number')
        num_games_actually_completed = completed_games_instances.count()
        
        if num_games_actually_completed == 0:
             for player in mk_event.participants.all():
                response_data['player_scores_per_game'][str(player.id)] = []
             response_data['num_games_played'] = 0
             return Response(response_data)

        for player in mk_event.participants.all():
            player_id_str = str(player.id)
            response_data['player_scores_per_game'][player_id_str] = []
            cumulative_score = 0
            
            for i in range(1, num_games_actually_completed + 1):
                game_for_this_number = completed_games_instances.filter(game_number=i).first()
                current_game_score_for_this_game_only = 0
                if game_for_this_number:
                    stat_entry = GamePlayerStats.objects.filter(game=game_for_this_number, player=player).first()
                    if stat_entry:
                        current_game_score_for_this_game_only = stat_entry.score_in_game
                
                cumulative_score += current_game_score_for_this_game_only
                response_data['player_scores_per_game'][player_id_str].append(cumulative_score)
        
        response_data['num_games_played'] = num_games_actually_completed
        return Response(response_data)

class ApplyBonusView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def post(self, request, pk=None):
        mk_event = get_object_or_404(MasterkillEvent, pk=pk)
        if mk_event.status != 'completed':
            return Response({"error": "Le Masterkill doit être terminé pour appliquer un bonus."}, status=status.HTTP_400_BAD_REQUEST)
        if not mk_event.has_bonus_reel:
             return Response({"error": "La roue des bonus n'est pas activée pour ce Masterkill."}, status=status.HTTP_400_BAD_REQUEST)

        player_id = request.data.get('player_id')
        bonus_points_str = request.data.get('bonus_points')
        if player_id is None or bonus_points_str is None:
            return Response({"error": "player_id et bonus_points sont requis."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            player_id = int(player_id); bonus_points = int(bonus_points_str)
        except ValueError:
            return Response({"error": "player_id et bonus_points doivent être des nombres valides."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            player_instance = Player.objects.get(pk=player_id)
            if player_instance not in mk_event.participants.all():
                return Response({"error": "Ce joueur ne participe pas à cet événement."}, status=status.HTTP_400_BAD_REQUEST)
            
            bonus_game, _ = Game.objects.get_or_create(
                masterkill_event=mk_event,
                game_number=mk_event.num_games_planned + 1000, # Pseudo-partie pour le bonus
                defaults={'status': 'completed', 'spawn_location': 'BonusRoue', 'kill_multiplier': 1.0}
            )
            bonus_stat, created_stat = GamePlayerStats.objects.update_or_create(
                game=bonus_game, player=player_instance,
                defaults={'score_in_game': bonus_points} # Met à jour ou crée le score bonus
            )
            if not created_stat: # Si l'entrée existait (multiples bonus pour le même joueur pour ce MK, ou relance)
                bonus_stat.score_in_game = F('score_in_game') + bonus_points # Cumuler les bonus
                bonus_stat.save()
            return Response({"message": f"Bonus de {bonus_points} appliqué à {player_instance.gamertag}."}, status=status.HTTP_200_OK)
        except Player.DoesNotExist:
            return Response({"error": "Joueur non trouvé."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class MasterkillKillsBySpawnView(APIView):
    permission_classes = [permissions.AllowAny]
    def get(self, request, pk=None):
        mk_event = get_object_or_404(MasterkillEvent, pk=pk)
        kills_by_spawn = GamePlayerStats.objects.filter(
            game__masterkill_event=mk_event, game__status='completed',
            game__spawn_location__isnull=False
        ).exclude(game__spawn_location__exact='').values(
            'game__spawn_location'
        ).annotate(
            total_kills_at_spawn=Sum('kills')
        ).order_by('-total_kills_at_spawn')
        
        data_for_response = [
            {'spawn_location': item['game__spawn_location'], 'total_kills': item['total_kills_at_spawn']}
            for item in kills_by_spawn if item['game__spawn_location']
        ]
        return Response(data_for_response)
    
class MasterkillEventCountView(APIView):
    permission_classes = [permissions.AllowAny] 

    def get(self, request):
        count = MasterkillEvent.objects.count()
        return Response({'count': count})