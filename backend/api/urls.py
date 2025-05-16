from django.urls import path
from . import views

app_name = 'api'

urlpatterns = [
    path('gages/', views.list_gages, name='gage-list'),
    path('masterkillevents/', views.MasterkillEventListCreateView.as_view(), name='masterkillevent-list-create'),
    path('masterkillevents/<int:pk>/', views.MasterkillEventRetrieveUpdateDestroyView.as_view(), name='masterkillevent-detail-update-destroy'),
    path('masterkillevents/<int:pk>/manage_game/', views.ManageGameView.as_view(), name='masterkillevent-manage-game'),
    path('masterkillevents/<int:pk>/aggregated-stats/', views.MasterkillAggregatedStatsView.as_view(), name='masterkillevent-aggregated-stats'),
    path('masterkillevents/<int:pk>/game-scores/', views.MasterkillGameScoresView.as_view(), name='masterkillevent-game-scores'),
    path('masterkillevents/<int:pk>/apply_bonus/', views.ApplyBonusView.as_view(), name='masterkillevent-apply-bonus'),
    path('masterkillevents/<int:pk>/kills-by-spawn/', views.MasterkillKillsBySpawnView.as_view(), name='masterkillevent-kills-by-spawn'),
    
    path('games/<int:game_pk>/complete/', views.EndGameAPIView.as_view(), name='game-complete'),
    
    path('redeployevents/', views.RedeployEventCreateView.as_view(), name='redeployevent-create'),
    path('reviveevents/', views.ReviveEventCreateView.as_view(), name='reviveevent-create'), # NOUVELLE URL
    
    path('rankings/all-time/', views.AllTimePlayerRankingView.as_view(), name='all-time-ranking'),
    
    path('users/me/', views.CurrentUserView.as_view(), name='current-user'),
    path('auth/register/', views.UserRegistrationView.as_view(), name='user-register'),
]