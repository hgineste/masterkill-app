from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth.models import User
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.db.models import Sum, Count, Q, F, FloatField, Case, When
from rest_framework.permissions import IsAuthenticated
from .serializers import UserSerializer 

from .serializers import UserRegistrationSerializer

from .models import Gage, MasterkillEvent, Player, Game, GamePlayerStats, RedeployEvent
from .serializers import (
    GageSerializer, MasterkillEventSerializer, PlayerSerializer,
    GameSerializer, RedeployEventSerializer, GamePlayerStatsSerializer,
    AggregatedPlayerStatsSerializer, AllTimePlayerStatsSerializer # AllTimePlayerStatsSerializer importé
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
    permission_classes = [IsAuthenticated] # Seuls les utilisateurs connectés peuvent accéder

    def get(self, request):
        serializer = UserSerializer(request.user) # Sérialise l'utilisateur connecté
        return Response(serializer.data)
    
class MasterkillAggregatedStatsView(APIView):
    def get(self, request, pk=None):
        mk_event = get_object_or_404(MasterkillEvent, pk=pk)
        completed_games = mk_event.games.filter(status='completed')

        aggregated_stats_list = []
        for player in mk_event.participants.all():
            player_data_serialized = PlayerSerializer(player).data

            stats = GamePlayerStats.objects.filter(
                game__in=completed_games,
                player=player
            ).aggregate(
                total_kills=Sum('kills', default=0),
                total_deaths=Sum('deaths', default=0),
                total_assists=Sum('assists', default=0),
                total_gulag_wins=Count('gulag_status', filter=Q(gulag_status='won')),
                total_revives_done=Sum('revives_done', default=0),
                total_times_executed_enemy=Sum('times_executed_enemy', default=0),
                total_times_got_executed=Sum('times_got_executed', default=0),
                total_rage_quits=Count('rage_quit', filter=Q(rage_quit=True)), # default=0 retiré
                total_times_redeployed_by_teammate=Sum('times_redeployed_by_teammate', default=0),
                total_score_from_games=Sum('score_in_game', default=0),
                games_played=Count('game', distinct=True) # default=0 retiré
            )

            # Construire le dictionnaire pour le serializer ou la réponse directe
            # Les agrégats Count retourneront 0 si rien n'est trouvé, Sum avec default=0 aussi.
            player_aggregated_data = {
                'player': player_data_serialized,
                'total_kills': stats['total_kills'],
                'total_deaths': stats['total_deaths'],
                'total_assists': stats['total_assists'],
                'total_gulag_wins': stats['total_gulag_wins'],
                'total_revives_done': stats['total_revives_done'],
                'total_times_executed_enemy': stats['total_times_executed_enemy'],
                'total_times_got_executed': stats['total_times_got_executed'],
                'total_rage_quits': stats['total_rage_quits'],
                'total_times_redeployed_by_teammate': stats['total_times_redeployed_by_teammate'],
                'total_score_from_games': stats['total_score_from_games'],
                'games_played': stats['games_played']
            }
            aggregated_stats_list.append(player_aggregated_data)

        # Si vous utilisez AggregatedPlayerStatsSerializer pour la sortie :
        serializer = AggregatedPlayerStatsSerializer(aggregated_stats_list, many=True)
        return Response(serializer.data)

class MasterkillEventListCreateView(generics.ListCreateAPIView):
    queryset = MasterkillEvent.objects.all().order_by('-created_at') 
    serializer_class = MasterkillEventSerializer 
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        participant_gamertags_list = serializer.validated_data.pop('participant_gamertags', [])
        creator = request.user if request.user.is_authenticated else None
        instance = serializer.save(creator=creator)
        player_instances = []
        if participant_gamertags_list:
            for gamertag_str in participant_gamertags_list:
                if gamertag_str and gamertag_str.strip():
                    player, _ = Player.objects.get_or_create(gamertag=gamertag_str.strip())
                    player_instances.append(player)
        if player_instances: instance.participants.set(player_instances)
        response_serializer = self.get_serializer(instance)
        headers = self.get_success_headers(response_serializer.data)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED, headers=headers)

class MasterkillEventRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = MasterkillEvent.objects.all()
    serializer_class = MasterkillEventSerializer

class ManageGameView(APIView):
    def post(self, request, pk=None):
        mk_event = get_object_or_404(MasterkillEvent, pk=pk)
        action_type = request.data.get('action')
        if action_type == 'start_next_game':
            if mk_event.status in ['completed', 'cancelled']: return Response({"error": "Ce MK est terminé ou annulé."}, status=status.HTTP_400_BAD_REQUEST)
            current_inprogress_game = mk_event.games.filter(status='inprogress').first()
            if current_inprogress_game: return Response(GameSerializer(current_inprogress_game).data, status=status.HTTP_200_OK)
            next_game_number = 1
            last_game = mk_event.games.order_by('-game_number').first()
            if last_game:
                if last_game.status == 'completed': next_game_number = last_game.game_number + 1
                else:
                    pending_game_to_start = mk_event.games.filter(status='pending', game_number=last_game.game_number).first()
                    if pending_game_to_start:
                        pending_game_to_start.status = 'inprogress'; pending_game_to_start.start_time = timezone.now(); pending_game_to_start.save()
                        if mk_event.status == 'pending': mk_event.status = 'inprogress'; mk_event.effective_start_at = timezone.now(); mk_event.save()
                        return Response(GameSerializer(pending_game_to_start).data, status=status.HTTP_200_OK)
                    else: return Response({"error": f"La partie {last_game.game_number} doit être gérée."}, status=status.HTTP_400_BAD_REQUEST)
            if next_game_number > mk_event.num_games_planned: return Response({"error": "Toutes les parties prévues ont été jouées."}, status=status.HTTP_400_BAD_REQUEST)
            game, created = Game.objects.get_or_create(masterkill_event=mk_event, game_number=next_game_number, defaults={'status': 'inprogress', 'start_time': timezone.now()})
            if not created and game.status != 'inprogress': game.status = 'inprogress'; game.start_time = timezone.now(); game.save()
            if mk_event.status == 'pending': mk_event.status = 'inprogress'; mk_event.effective_start_at = timezone.now(); mk_event.save()
            return Response(GameSerializer(game).data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
        return Response({"error": "Action non reconnue dans manage_game."}, status=status.HTTP_400_BAD_REQUEST)

class RedeployEventCreateView(generics.CreateAPIView):
    queryset = RedeployEvent.objects.all()
    serializer_class = RedeployEventSerializer
    def perform_create(self, serializer):
        redeploy_event = serializer.save()
        stats, _ = GamePlayerStats.objects.get_or_create(game=redeploy_event.game, player=redeploy_event.redeployed_player)
        stats.times_redeployed_by_teammate = (stats.times_redeployed_by_teammate or 0) + 1
        stats.save()

class EndGameAPIView(APIView):
    def post(self, request, game_pk=None):
        game_instance = get_object_or_404(Game, pk=game_pk)
        mk_event = game_instance.masterkill_event
        if game_instance.status == 'completed': return Response({"message": "Cette partie est déjà terminée."}, status=status.HTTP_400_BAD_REQUEST)
        if mk_event.status != 'inprogress': return Response({"error": "Le Masterkill n'est pas en cours."}, status=status.HTTP_400_BAD_REQUEST)
        player_stats_data_list = request.data.get('player_stats', [])
        if not isinstance(player_stats_data_list, list): return Response({"error": "Le champ 'player_stats' doit être une liste."}, status=status.HTTP_400_BAD_REQUEST)
        for player_data in player_stats_data_list:
            if not player_data: continue
            player_id = player_data.get('player_id')
            if not player_id: continue
            try: player_instance = Player.objects.get(pk=player_id)
            except Player.DoesNotExist: continue
            kills = int(player_data.get('kills', 0)); deaths = int(player_data.get('deaths', 0)); assists = int(player_data.get('assists', 0))
            gulag_status = player_data.get('gulag_status', 'not_played')
            revives_done = int(player_data.get('revives_done', 0)); times_executed_enemy = int(player_data.get('times_executed_enemy', 0))
            times_got_executed = int(player_data.get('times_got_executed', 0)); rage_quit = bool(player_data.get('rage_quit', False))
            times_redeployed_by_teammate = int(player_data.get('times_redeployed_by_teammate', 0))
            score = 0; score += kills * mk_event.points_kill; score += revives_done * mk_event.points_rea
            if gulag_status == 'won': score += mk_event.points_goulag_win
            score += times_redeployed_by_teammate * mk_event.points_redeploiement
            if rage_quit: score += mk_event.points_rage_quit
            score += times_executed_enemy * mk_event.points_execution; score += times_got_executed * mk_event.points_humiliation
            stats_defaults = {
                'kills': kills, 'deaths': deaths, 'assists': assists, 'gulag_status': gulag_status,
                'revives_done': revives_done, 'times_executed_enemy': times_executed_enemy,
                'times_got_executed': times_got_executed, 'rage_quit': rage_quit,
                'times_redeployed_by_teammate': times_redeployed_by_teammate, 'score_in_game': score
            }
            GamePlayerStats.objects.update_or_create(game=game_instance, player=player_instance, defaults=stats_defaults)
        game_instance.status = 'completed'; game_instance.end_time = timezone.now(); game_instance.save()
        completed_games_count = mk_event.games.filter(status='completed').count()
        mk_status_updated_to_completed = False
        if completed_games_count >= mk_event.num_games_planned:
            mk_event.status = 'completed'; mk_event.ended_at = timezone.now(); mk_event.save()
            mk_status_updated_to_completed = True
        return Response({
            "message": f"Partie {game_instance.game_number} terminée.", "game_id": game_instance.id,
            "game_status": game_instance.status, "mk_status": mk_event.status,
            "mk_ended": mk_status_updated_to_completed
        }, status=status.HTTP_200_OK)

class AllTimePlayerRankingView(generics.ListAPIView):
    serializer_class = AllTimePlayerStatsSerializer

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
            kd_ratio = round((stats['total_kills'] or 0) / (stats['total_deaths'] or 1), 2) if (stats['total_deaths'] or 0) > 0 else (stats['total_kills'] or 0)

            # Créez un dictionnaire qui correspond aux champs de votre sérialiseur
            player_data = {
                'player_id': player.id,
                'gamertag': player.gamertag,
                'total_score': stats['total_score'],
                'total_kills': stats['total_kills'],
                'total_deaths': stats['total_deaths'],
                'total_assists': stats['total_assists'],
                'total_revives_done': stats['total_revives_done'],
                'total_gulag_wins': stats['total_gulag_wins'],
                'total_rage_quits': stats['total_rage_quits'],
                'total_times_redeployed': stats['total_times_redeployed'],
                'games_played': stats['games_played'],
                'mks_won': mks_won,
                'kd_ratio': kd_ratio
            }
            player_rankings.append(player_data)
        player_rankings.sort(key=lambda x: x['total_score'], reverse=True)
        return player_rankings


class MasterkillGameScoresView(APIView):
    def get(self, request, pk=None):
        mk_event = get_object_or_404(MasterkillEvent, pk=pk)
        response_data = {
            'mk_id': mk_event.id, 'mk_name': mk_event.name, 'num_games_planned': mk_event.num_games_planned,
            'participants': PlayerSerializer(mk_event.participants.all(), many=True).data,
            'player_scores_per_game': {}
        }
        completed_games = mk_event.games.filter(status='completed').order_by('game_number')
        for player in mk_event.participants.all():
            player_id_str = str(player.id)
            response_data['player_scores_per_game'][player_id_str] = []
            cumulative_score = 0
            for i in range(1, mk_event.num_games_planned + 1):
                game_for_this_number = completed_games.filter(game_number=i).first()
                current_game_score = 0
                if game_for_this_number:
                    stat_entry = GamePlayerStats.objects.filter(game=game_for_this_number, player=player).first()
                    if stat_entry: current_game_score = stat_entry.score_in_game
                cumulative_score += current_game_score
                response_data['player_scores_per_game'][player_id_str].append(cumulative_score)
        return Response(response_data)