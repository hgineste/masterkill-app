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

from .models import Gage, MasterkillEvent, Player, Game, GamePlayerStats, RedeployEvent
from .serializers import (
    GageSerializer, MasterkillEventSerializer, PlayerSerializer,
    GameSerializer, RedeployEventSerializer, GamePlayerStatsSerializer,
    AggregatedPlayerStatsSerializer, AllTimePlayerStatsSerializer,
    UserRegistrationSerializer, UserSerializer
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
    permission_classes = [permissions.AllowAny] # Ou IsAuthenticated
    def get(self, request, pk=None):
        mk_event = get_object_or_404(MasterkillEvent, pk=pk)
        completed_games = mk_event.games.filter(status='completed')
        aggregated_stats_list = []
        for player in mk_event.participants.all():
            player_data_serialized = PlayerSerializer(player).data
            stats = GamePlayerStats.objects.filter(
                game__in=completed_games, player=player
            ).aggregate(
                total_kills=Sum('kills', default=0),
                total_deaths=Sum('deaths', default=0),
                total_assists=Sum('assists', default=0),
                total_gulag_wins=Count('gulag_status', filter=Q(gulag_status='won')),
                total_gulag_lost=Count('gulag_status', filter=Q(gulag_status='lost')),
                total_revives_done=Sum('revives_done', default=0),
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
                'total_revives_done': stats['total_revives_done'],
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
                # Si elle existait déjà mais n'était pas 'pending', c'est une situation anormale
                if not created and next_game_to_start.status != 'pending':
                     return Response({"error": f"La partie {next_game_number} existe déjà avec un statut inattendu: {next_game_to_start.status}."}, status=status.HTTP_400_BAD_REQUEST)


            next_game_to_start.status = 'inprogress'
            next_game_to_start.start_time = timezone.now()
            
            next_game_to_start.determine_and_set_kill_multiplier() # Appel de la méthode du modèle
            
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
        game_spawn_location = request.data.get('spawn_location', None) # Récupérer le spawn_location

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
            revives_done = int(player_data.get('revives_done', 0))
            times_executed_enemy = int(player_data.get('times_executed_enemy', 0))
            times_got_executed = int(player_data.get('times_got_executed', 0))
            rage_quit = bool(player_data.get('rage_quit', False))
            times_redeployed_by_teammate = int(player_data.get('times_redeployed_by_teammate', 0))

            score = 0
            score += (kills * mk_event.points_kill * game_instance.kill_multiplier)
            score += revives_done * mk_event.points_rea
            if gulag_status == 'won':
                score += mk_event.points_goulag_win
            score += times_redeployed_by_teammate * mk_event.points_redeploiement
            if rage_quit:
                score += mk_event.points_rage_quit
            score += times_executed_enemy * mk_event.points_execution
            score += times_got_executed * mk_event.points_humiliation
            
            stats_defaults = {
                'kills': kills, 'deaths': deaths, 'assists': player_data.get('assists', 0),
                'gulag_status': gulag_status, 'revives_done': revives_done,
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
        if game_spawn_location and game_spawn_location.strip(): # Enregistrer le spawn_location
            game_instance.spawn_location = game_spawn_location.strip()
        game_instance.save()

        completed_games_count = mk_event.games.filter(status='completed').count()
        mk_status_updated_to_completed = False
        if completed_games_count >= mk_event.num_games_planned:
            mk_event.status = 'completed'
            mk_event.ended_at = timezone.now()
            # Ajouter ici la logique pour déterminer et sauvegarder le mk_event.winner
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
            stats = GamePlayerStats.objects.filter(player=player, game__status='completed').aggregate(
                total_score=Sum('score_in_game', default=0),
                total_kills=Sum('kills', default=0),
                total_deaths=Sum('deaths', default=0),
                total_assists=Sum('assists', default=0),
                total_revives_done=Sum('revives_done', default=0),
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
                'total_revives_done': stats['total_revives_done'], 'total_gulag_wins': stats['total_gulag_wins'],
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