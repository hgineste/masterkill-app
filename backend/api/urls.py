from django.urls import path
from . import views # S'assure que UserRegistrationView est dans api/views.py

app_name = 'api' # Optionnel, mais une bonne pratique

urlpatterns = [
    # Vos URLs existantes pour les gages, masterkillevents, etc.
    path('gages/', views.list_gages, name='gage-list'),
    path('masterkillevents/', views.MasterkillEventListCreateView.as_view(), name='masterkillevent-list-create'),
    path('masterkillevents/<int:pk>/', views.MasterkillEventRetrieveUpdateDestroyView.as_view(), name='masterkillevent-detail-update-destroy'),
    path('masterkillevents/<int:pk>/manage_game/', views.ManageGameView.as_view(), name='masterkillevent-manage-game'),
    path('redeployevents/', views.RedeployEventCreateView.as_view(), name='redeployevent-create'),
    path('games/<int:game_pk>/complete/', views.EndGameAPIView.as_view(), name='game-complete'),
    path('masterkillevents/<int:pk>/aggregated-stats/', views.MasterkillAggregatedStatsView.as_view(), name='masterkillevent-aggregated-stats'),
    path('masterkillevents/<int:pk>/game-scores/', views.MasterkillGameScoresView.as_view(), name='masterkillevent-game-scores'),
    path('rankings/all-time/', views.AllTimePlayerRankingView.as_view(), name='all-time-ranking'),
    path('users/me/', views.CurrentUserView.as_view(), name='current-user'),

    # Endpoint pour l'inscription utilisateur
    path('auth/register/', views.UserRegistrationView.as_view(), name='user-register'),
]