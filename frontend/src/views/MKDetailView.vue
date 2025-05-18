<script setup>
import { ref, onMounted, computed, watch } from 'vue';
import { useRoute, useRouter, RouterLink } from 'vue-router';
import apiClient from '@/services/apiClient';
import logoWarzone from '@/assets/images/logo-warzone.png';
import mapWarzoneImage from '@/assets/images/map_warzone_placeholder.jpg';

import { Line } from 'vue-chartjs';
import {
  Chart as ChartJS, Title, Tooltip, Legend, LineElement,
  CategoryScale, LinearScale, PointElement, Filler
} from 'chart.js';

ChartJS.register(Title, Tooltip, Legend, LineElement, CategoryScale, LinearScale, PointElement, Filler);

const route = useRoute();
const router = useRouter();
const mkId = ref(route.params.id);

const masterkillEvent = ref(null);
const isLoading = ref(true);
const error = ref(null);

const currentGameStats = ref({});
const activeGame = ref(null);
const mkAggregatedStats = ref([]);

const showRedeployLogForm = ref(false);
const redeployData = ref({ redeployer_player_id: null, redeployed_player_id: null });
const redeployError = ref(null);

const showReviveLogForm = ref(false);
const reviveData = ref({ reviver_player_id: null, revived_player_id: null });
const reviveError = ref(null);

const gulagOptions = ref([
  { value: 'not_played', text: 'Non Joué / Fermé' },
  { value: 'won', text: 'Gagné' },
  { value: 'lost', text: 'Perdu' },
]);

const mapLocations = ref({
  'Airport': { name: 'Airport', x: 15, y: 25 },
  'Stadium': { name: 'Stadium', x: 50, y: 30 },
  'Downtown': { name: 'Downtown', x: 45, y: 60 },
  'Superstore': { name: 'Superstore', x: 35, y: 50 },
});
const selectedMapLocation = ref(null);
const gameSpawnLocationInput = ref('');

const gameByGameScoresDataDetail = ref(null);
const isLoadingGraphDataDetail = ref(false);
const chartLabelsDetail = ref([]);
const chartDatasetsDetail = ref([]);
const chartInstanceDetailRef = ref(null);

const killsBySpawnData = ref([]);
const isLoadingKillsBySpawn = ref(false);

const chartDataDetail = computed(() => ({ labels: chartLabelsDetail.value, datasets: chartDatasetsDetail.value }));
const chartOptionsDetail = ref({
  responsive: true, maintainAspectRatio: false, tension: 0.4,
  animation: { duration: 0 },
  scales: {
    y: { beginAtZero: true, ticks: { color: 'var(--wz-text-medium)', padding: 5 }, grid: { color: 'var(--wz-border-color)' } },
    x: { ticks: { color: 'var(--wz-text-medium)', padding: 5 }, grid: { color: 'var(--wz-border-color)' } }
  },
  plugins: {
    legend: { display: true, position: 'bottom', labels: { color: 'var(--wz-text-light)'} },
    tooltip: { titleFont: { weight: 'bold'}, bodyFont: {size: 14} },
  }
});

watch(activeGame, (newVal, oldVal) => {
  if ((newVal && newVal.id && (newVal.status === 'inprogress' || newVal.status === 'pending')) || (!newVal && oldVal)) {
     if (!oldVal || newVal.id !== oldVal.id || (newVal.status === 'pending' && oldVal.status !== 'pending') || (newVal.status === 'inprogress' && oldVal.status !== 'inprogress') || !newVal ) {
        initializeCurrentGameStats();
        gameSpawnLocationInput.value = newVal?.spawn_location || '';
     }
  } else if (newVal && newVal.status === 'pending') {
    gameSpawnLocationInput.value = '';
  }
}, { deep: true });

async function fetchAggregatedStats() {
  if (!masterkillEvent.value || masterkillEvent.value.status === 'pending') {
    mkAggregatedStats.value = []; return;
  }
  try {
    const response = await apiClient.get(`/masterkillevents/${mkId.value}/aggregated-stats/`);
    mkAggregatedStats.value = response.data || [];
  } catch (err) {
    console.error("Erreur fetch stats agrégées:", err.response?.data || err.message || err);
    mkAggregatedStats.value = [];
    // Ne pas écraser l'erreur principale de fetchMKDetails ici, sauf si c'est une erreur spécifique à cette étape
  }
}

async function fetchKillsBySpawn() {
  if (!masterkillEvent.value || masterkillEvent.value.status !== 'completed') {
    killsBySpawnData.value = [];
    return;
  }
  isLoadingKillsBySpawn.value = true;
  try {
    const response = await apiClient.get(`/masterkillevents/${mkId.value}/kills-by-spawn/`);
    killsBySpawnData.value = response.data || [];
  } catch (err) {
    console.error("Erreur fetch kills par spawn:", err.response?.data || err.message || err);
    killsBySpawnData.value = [];
  } finally {
    isLoadingKillsBySpawn.value = false;
  }
}

async function fetchMKDetails(resetStatsIfNeeded = true) {
  isLoading.value = true; error.value = null;
  masterkillEvent.value = null; 
  activeGame.value = null;    
  mkAggregatedStats.value = []; 
  killsBySpawnData.value = [];
  
  let initialActiveGameId = activeGame.value?.id; 
  let initialActiveGameStatus = activeGame.value?.status;

  try {
    const response = await apiClient.get(`/masterkillevents/${mkId.value}/`);
    if (!response.data) {
      error.value = `Aucune donnée reçue pour l'événement MK ${mkId.value}.`;
      isLoading.value = false; return;
    }
    masterkillEvent.value = response.data;

    if (!masterkillEvent.value) { // Double vérification si response.data était un objet vide non null
        error.value = `Données MK invalides pour l'ID ${mkId.value}.`;
        isLoading.value = false; return;
    }
    
    const gameInfoFromServer = masterkillEvent.value.current_game_info;

    if (gameInfoFromServer && (gameInfoFromServer.id !== undefined || gameInfoFromServer.status === 'pending')) { // Vérifier existence de id
      activeGame.value = gameInfoFromServer;
      gameSpawnLocationInput.value = gameInfoFromServer.spawn_location || '';
    } else if (masterkillEvent.value.status === 'pending') {
      activeGame.value = { game_number: 1, status: 'pending', id: null, masterkill_event: mkId.value, kill_multiplier: 1.0, spawn_location: '' };
      gameSpawnLocationInput.value = '';
    } else if (masterkillEvent.value.status === 'inprogress' && !gameInfoFromServer) {
      const completedGames = masterkillEvent.value.games?.filter(g => g.status === 'completed').length || 0;
      if (completedGames < masterkillEvent.value.num_games_planned) {
        activeGame.value = { game_number: completedGames + 1, status: 'pending', id: null, masterkill_event: mkId.value, kill_multiplier: 1.0, spawn_location: '' };
        gameSpawnLocationInput.value = '';
      } else { activeGame.value = null; }
    } else { activeGame.value = null; }

    if (masterkillEvent.value.status !== 'pending') {
      await fetchAggregatedStats();
    } else { mkAggregatedStats.value = []; }

     if (resetStatsIfNeeded) {
       const gameChanged = !activeGame.value || activeGame.value.id !== initialActiveGameId || (activeGame.value.id === initialActiveGameId && activeGame.value.status === 'pending' && initialActiveGameStatus !== 'pending');
       const isNewGameScenario = gameChanged && (activeGame.value?.status !== 'inprogress' || !initialActiveGameId || activeGame.value.id !== initialActiveGameId);
       if (isNewGameScenario) { initializeCurrentGameStats(); }
     }

     if (masterkillEvent.value && masterkillEvent.value.status === 'completed') {
        await fetchGameByGameScoresForDetailChart();
        await fetchKillsBySpawn();
     }

  } catch (err) {
    console.error(`Erreur détaillée lors du chargement de MK ${mkId.value}:`, err.response || err.message || err);
    error.value = `Impossible de charger les détails du MK ${mkId.value}. Erreur API ou données manquantes.`;
    masterkillEvent.value = null; 
  } finally { isLoading.value = false; }
}

function initializeCurrentGameStats() {
  if (masterkillEvent.value?.participants_details) {
    const stats = {};
    masterkillEvent.value.participants_details.forEach(user => { // participants_details sont maintenant des User
      stats[user.id] = {
        kills: 0, deaths: 0, assists: 0, gulag_status: 'not_played',
        revives_done: 0, times_executed_enemy: 0, times_got_executed: 0,
        rage_quit: false, times_redeployed_by_teammate: 0,
      };
    });
    currentGameStats.value = stats;
  } else { currentGameStats.value = {}; }
}

function changeStat(playerId, statName, delta) {
  if (currentGameStats.value[playerId]?.[statName] !== undefined && typeof currentGameStats.value[playerId][statName] === 'number') {
    const newValue = currentGameStats.value[playerId][statName] + delta;
    if (statName !== 'score_in_game') {
        currentGameStats.value[playerId][statName] = Math.max(0, newValue);
    } else {
        currentGameStats.value[playerId][statName] = newValue;
    }
  }
}
function updateGulagStatus(playerId, newStatus) {
  if (currentGameStats.value[playerId]) {
    currentGameStats.value[playerId].gulag_status = newStatus;
  }
}
function toggleRageQuit(playerId) {
  if (currentGameStats.value[playerId] && typeof currentGameStats.value[playerId]['rage_quit'] === 'boolean') {
    currentGameStats.value[playerId]['rage_quit'] = !currentGameStats.value[playerId]['rage_quit'];
  }
}

async function startOrManageGame(actionToDo = 'start_next_game') {
  if (!masterkillEvent.value) {
    error.value = "Données du Masterkill non chargées pour démarrer la partie.";
    return;
  }
  isLoading.value = true;
  error.value = null;
  try {
    const response = await apiClient.post(`/masterkillevents/${mkId.value}/manage_game/`, { action: actionToDo });
    activeGame.value = response.data; 
    if (masterkillEvent.value.status === 'pending' && activeGame.value?.status === 'inprogress') {
      masterkillEvent.value.status = 'inprogress';
    }
    await fetchMKDetails(true); 
  } catch (err) {
    console.error(`Erreur action '${actionToDo}':`, err.response?.data || err.message || err);
    error.value = `Erreur action '${actionToDo}': ${err.response?.data?.error || err.message}`;
    alert(`Erreur action '${actionToDo}': ${err.response?.data?.error || err.message}`);
    await fetchMKDetails(false);
  } finally {
    isLoading.value = false;
  }
}

async function handleMKStatusChange(newStatus) {
  if (!masterkillEvent.value) return;
  isLoading.value = true;
  try {
    await apiClient.patch(`/masterkillevents/${masterkillEvent.value.id}/`, { status: newStatus });
    await fetchMKDetails(newStatus === 'pending');
    if (newStatus === 'completed' && masterkillEvent.value?.status === 'completed') {
      await fetchAggregatedStats();
      router.push({ name: 'masterkill-results', params: { id: mkId.value } });
    }
  } catch (err) {
    alert(`Erreur màj statut MK: ${err.message}`);
    await fetchMKDetails(false);
  } finally { isLoading.value = false; }
}

function startFirstGameOrNext() { startOrManageGame('start_next_game'); }
function pauseMK() { handleMKStatusChange('paused'); }
function resumeMK() { handleMKStatusChange('inprogress'); }
async function endMK() { if(confirm("Terminer ce Masterkill ?")) { await handleMKStatusChange('completed'); }}

async function logRedeployEvent() {
  redeployError.value = null;
  if (!activeGame.value?.id) { redeployError.value = "Partie non active."; return; }
  if (!redeployData.value.redeployer_player_id || !redeployData.value.redeployed_player_id) {
    redeployError.value = "Sélectionner les deux joueurs."; return;
  }
  if (redeployData.value.redeployer_player_id === redeployData.value.redeployed_player_id) {
    redeployError.value = "Un joueur ne peut se redéployer lui-même."; return;
  }
  const payload = { game: activeGame.value.id, redeployer_player: redeployData.value.redeployer_player_id, redeployed_player: redeployData.value.redeployed_player_id };
  try {
    isLoading.value = true;
    await apiClient.post('/redeployevents/', payload);
    const redeployedPlayerId = payload.redeployed_player;
    if (currentGameStats.value[redeployedPlayerId]) {
      currentGameStats.value[redeployedPlayerId].times_redeployed_by_teammate = (currentGameStats.value[redeployedPlayerId].times_redeployed_by_teammate || 0) + 1;
    }
    alert(`Redéploiement enregistré !`);
    redeployData.value = { redeployer_player_id: null, redeployed_player_id: null };
    showRedeployLogForm.value = false;
  } catch (err) {
    redeployError.value = `Erreur serveur: ${err.response?.data?.detail || err.message}`;
  } finally { isLoading.value = false; }
}

async function logReviveEvent() {
  reviveError.value = null;
  if (!activeGame.value?.id) { reviveError.value = "Partie non active."; return; }
  if (!reviveData.value.reviver_player_id || !reviveData.value.revived_player_id) {
    reviveError.value = "Sélectionner les deux joueurs pour la réanimation."; return;
  }
  if (reviveData.value.reviver_player_id === reviveData.value.revived_player_id) {
    reviveError.value = "Un joueur ne peut se réanimer lui-même de cette manière."; return;
  }
  const payload = { 
    game: activeGame.value.id, 
    reviver_player: reviveData.value.reviver_player_id, 
    revived_player: reviveData.value.revived_player_id 
  };
  try {
    isLoading.value = true; 
    await apiClient.post('/reviveevents/', payload);
    const reviverPlayerId = payload.reviver_player;
    if (currentGameStats.value[reviverPlayerId]) {
      currentGameStats.value[reviverPlayerId].revives_done = (currentGameStats.value[reviverPlayerId].revives_done || 0) + 1;
    }
    alert(`Réanimation enregistrée !`);
    reviveData.value = { reviver_player_id: null, revived_player_id: null };
    showReviveLogForm.value = false;
  } catch (err) {
    reviveError.value = `Erreur serveur lors du log de réanimation: ${err.response?.data?.detail || err.message}`;
  } finally {
    isLoading.value = false;
  }
}

async function handleEndGame() {
  if (!activeGame.value || activeGame.value.status !== 'inprogress') {
    alert("Aucune partie en cours à terminer."); return;
  }
  if (!masterkillEvent.value?.participants_details) {
    alert("Données participants manquantes."); return;
  }
  if (!confirm(`Terminer Partie ${activeGame.value.game_number} et enregistrer scores (Spawn: ${gameSpawnLocationInput.value || 'Non défini'}) ?`)) return;

  const playerStatsPayloadList = masterkillEvent.value.participants_details.map(user => { // Utiliser user car participants_details sont des User
    const stats = currentGameStats.value[user.id] || {};
    return {
      player_id: user.id, kills: stats.kills || 0, deaths: stats.deaths || 0,
      assists: stats.assists || 0, 
      gulag_status: stats.gulag_status || 'not_played',
      revives_done: stats.revives_done || 0, 
      times_executed_enemy: stats.times_executed_enemy || 0,
      times_got_executed: stats.times_got_executed || 0, rage_quit: stats.rage_quit || false,
      times_redeployed_by_teammate: stats.times_redeployed_by_teammate || 0,
    };
  });
  isLoading.value = true;
  try {
    const payloadForEndGame = { 
        player_stats: playerStatsPayloadList,
        spawn_location: gameSpawnLocationInput.value || null 
    };
    const response = await apiClient.post(
      `/games/${activeGame.value.id}/complete/`,
      payloadForEndGame
    );
    alert(response.data.message || "Partie terminée!");
    gameSpawnLocationInput.value = '';

    if (response.data.mk_ended || response.data.mk_status === 'completed') {
      await fetchMKDetails(false);
      router.push({ name: 'masterkill-results', params: { id: mkId.value } });
    } else {
      await fetchMKDetails(true);
    }
  } catch (err) {
    alert(`Erreur fin de partie: ${err.response?.data?.error || err.message}`);
    await fetchMKDetails(false);
  } finally { isLoading.value = false; }
}

async function fetchGameByGameScoresForDetailChart() {
  if (!masterkillEvent.value || masterkillEvent.value.status !== 'completed') {
    chartLabelsDetail.value = []; chartDatasetsDetail.value = []; return;
  }
  isLoadingGraphDataDetail.value = true;
  try {
    const response = await apiClient.get(`/masterkillevents/${mkId.value}/game-scores/`);
    gameByGameScoresDataDetail.value = response.data;
    if (gameByGameScoresDataDetail.value?.player_scores_per_game) {
        prepareChartDataForDetail();
    } else { chartLabelsDetail.value = []; chartDatasetsDetail.value = []; }
  } catch (err) { console.error("Erreur fetch scores par partie pour détail:", err); }
  finally { isLoadingGraphDataDetail.value = false; }
}

function prepareChartDataForDetail() {
  if (!gameByGameScoresDataDetail.value || !masterkillEvent.value?.participants_details) {
    chartLabelsDetail.value = []; chartDatasetsDetail.value = []; return;
  }
  const numGames = gameByGameScoresDataDetail.value.num_games_played ?? masterkillEvent.value.num_games_planned ?? 0;
  const participants = gameByGameScoresDataDetail.value.participants || masterkillEvent.value.participants_details;
  const scoresPerGame = gameByGameScoresDataDetail.value.player_scores_per_game;

  if (!participants || participants.length === 0) { return; }
  
  if (numGames === 0 && mkAggregatedStats.value.length > 0) {
    chartLabelsDetail.value = ["Début", "Score Final"];
    chartDatasetsDetail.value = participants.map(user => { // user au lieu de player
        const r = Math.floor(Math.random() * 180) + 75; const g = Math.floor(Math.random() * 180) + 75; const b = Math.floor(Math.random() * 180) + 75;
        const aggPlayerStat = mkAggregatedStats.value.find(s => s.player.id === user.id); // s.player.id (User)
        const finalScoreFromAgg = aggPlayerStat ? (aggPlayerStat.total_score_from_games || 0) : 0;
        return {
            label: user.username, data: [0, finalScoreFromAgg], borderColor: `rgb(${r},${g},${b})`, // user.username
            backgroundColor: `rgba(${r},${g},${b},0.15)`, tension: 0.4, fill: 'origin',
            pointRadius: 5, pointBackgroundColor: `rgb(${r},${g},${b})`,
            pointHoverRadius: 7, pointHoverBorderWidth: 2, borderWidth: 3,
        };
    });
    return;
  }
  
  chartLabelsDetail.value = ["Début", ...Array.from({ length: numGames }, (_, i) => `Partie ${i + 1}`), "Score Final"];
  
  chartDatasetsDetail.value = participants.map(user => { // user au lieu de player
    const r = Math.floor(Math.random() * 180) + 75; const g = Math.floor(Math.random() * 180) + 75; const b = Math.floor(Math.random() * 180) + 75;
    const playerData = [0];
    const playerScoresForGames = scoresPerGame[user.id.toString()] || []; // user.id
    
    for (let i = 0; i < numGames; i++) {
        const scoreForThisGame = playerScoresForGames[i] !== undefined ? playerScoresForGames[i] : (playerData.length > 0 ? playerData[playerData.length -1] : 0) ;
        playerData.push(scoreForThisGame);
    }
    const aggPlayerStat = mkAggregatedStats.value.find(s => s.player.id === user.id); // s.player.id (User)
    const finalScoreFromAgg = aggPlayerStat ? (aggPlayerStat.total_score_from_games || 0) : (playerData.length > 0 ? playerData[playerData.length -1] : 0);
    playerData.push(finalScoreFromAgg);

    return {
      label: user.username, data: playerData, borderColor: `rgb(${r},${g},${b})`, // user.username
      backgroundColor: `rgba(${r},${g},${b},0.15)`, tension: 0.4, fill: 'origin',
      pointRadius: 5, pointBackgroundColor: `rgb(${r},${g},${b})`,
      pointHoverRadius: 7, pointHoverBorderWidth: 2, borderWidth: 3,
    };
  });
}

onMounted(() => {
  fetchMKDetails();
});

const canStartCurrentPendingGame = computed(() => masterkillEvent.value && (masterkillEvent.value.status === 'pending' || masterkillEvent.value.status === 'inprogress') && activeGame.value?.status === 'pending');
const canPauseMK = computed(() => masterkillEvent.value?.status === 'inprogress' && activeGame.value?.status === 'inprogress');
const canResumeMK = computed(() => masterkillEvent.value?.status === 'paused');
const isGameCurrentlyInProgress = computed(() => masterkillEvent.value?.status === 'inprogress' && activeGame.value?.status === 'inprogress');
const canEndCurrentGame = computed(() => isGameCurrentlyInProgress.value && activeGame.value?.id );
const showExplicitNextGameButton = computed(() => {
    if (!masterkillEvent.value || !activeGame.value) return false;
    return masterkillEvent.value.status === 'inprogress' &&
           activeGame.value.status === 'completed' &&
           (activeGame.value.game_number || 0) < masterkillEvent.value.num_games_planned;
});
const canEndMK = computed(() => {
  return masterkillEvent.value &&
         (masterkillEvent.value.status === 'inprogress' || masterkillEvent.value.status === 'paused');
});
const availablePlayersForEvents = computed(() => masterkillEvent.value?.participants_details || []); // Renommé pour plus de clarté
const currentDisplayedGameNumber = computed(() => {
    if (activeGame.value && (activeGame.value.status === 'pending' || activeGame.value.status === 'inprogress')) return activeGame.value.game_number;
    if (masterkillEvent.value?.status === 'pending') return 1;
    if (masterkillEvent.value?.status === 'inprogress') {
        const completedGames = masterkillEvent.value.games?.filter(g => g.status === 'completed').length || 0;
        if (completedGames < masterkillEvent.value.num_games_planned) return completedGames + 1;
    }
    return '...';
});
const completedGamesCountInMK = computed(() => masterkillEvent.value?.games?.filter(g => g.status === 'completed').length || 0);

const showScoreSummaryTable = computed(() => {
  return masterkillEvent.value &&
         mkAggregatedStats.value.length > 0 &&
         (
           masterkillEvent.value.status === 'paused' ||
           (masterkillEvent.value.status === 'inprogress' && activeGame.value?.status === 'completed') ||
           (masterkillEvent.value.status === 'inprogress' && activeGame.value?.status === 'pending' && completedGamesCountInMK.value > 0)
         );
});

const rankedPlayerScoresSoFar = computed(() => {
  if (!mkAggregatedStats.value || mkAggregatedStats.value.length === 0) return [];
  return [...mkAggregatedStats.value]
    .sort((a, b) => (b.total_score_from_games || 0) - (a.total_score_from_games || 0))
    .map((pStat, index) => ({
      rank: index + 1, 
      gamertag: pStat.player.username, // Utiliser username
      totalScore: pStat.total_score_from_games || 0, 
      playerId: pStat.player.id
    }));
});

const determinedWinnerGamertag = computed(() => {
  if (masterkillEvent.value?.winner_details?.username) { // Utiliser username
    return masterkillEvent.value.winner_details.username;
  }
  if (masterkillEvent.value?.status === 'completed' && rankedPlayerScoresSoFar.value.length > 0) {
    return rankedPlayerScoresSoFar.value[0].gamertag; // rankedPlayerScoresSoFar utilise déjà username pour gamertag
  }
  return 'Non déterminé';
});

function calculateKDRatio(kills, deaths) {
  const k = Number(kills) || 0;
  const d = Number(deaths) || 0;
  if (d === 0) return k > 0 ? '∞' : (0).toFixed(2);
  return (k / d).toFixed(2);
}

const durationOfMK = computed(() => {
  if (masterkillEvent.value && masterkillEvent.value.effective_start_at && masterkillEvent.value.ended_at) {
    const start = new Date(masterkillEvent.value.effective_start_at);
    const end = new Date(masterkillEvent.value.ended_at);
    const durationMs = end - start;
    const hours = Math.floor(durationMs / (1000 * 60 * 60));
    const minutes = Math.floor((durationMs % (1000 * 60 * 60)) / (1000 * 60));
    return `${hours}h ${minutes}min`;
  }
  return 'N/A';
});

const averageKillsPerGameOverall = computed(() => {
    if (masterkillEvent.value && mkAggregatedStats.value.length > 0 && completedGamesCountInMK.value > 0) {
        const totalKillsAllPlayers = mkAggregatedStats.value.reduce((sum, pStat) => sum + (pStat.total_kills || 0), 0);
        return (totalKillsAllPlayers / completedGamesCountInMK.value).toFixed(1);
    }
    return 'N/A';
});

const detailedPlayerStats = computed(() => {
  if (!mkAggregatedStats.value || mkAggregatedStats.value.length === 0 || !masterkillEvent.value) return [];
  return mkAggregatedStats.value.map(pStat => {
    const user = pStat.player; // pStat.player est maintenant un objet User {id, username}
    const kills = pStat.total_kills || 0;
    const deaths = pStat.total_deaths || 0;
    const gamesPlayed = pStat.games_played_in_mk ?? completedGamesCountInMK.value ?? 0;
    const gulagWins = pStat.total_gulag_wins || 0;
    const gulagLost = pStat.total_gulag_lost || 0; 

    return {
      id: user.id,
      gamertag: user.username, // Utiliser username pour l'affichage
      total_kills: kills,
      total_deaths: deaths,
      kd_ratio: calculateKDRatio(kills, deaths),
      total_assists: pStat.total_assists || 0, 
      total_revives_done: pStat.total_revives_done || 0, // Ceci viendra de ReviveEvent count
      average_kills_per_game: gamesPlayed > 0 ? (kills / gamesPlayed).toFixed(1) : '0.0',
      total_gulag_wins: gulagWins,
      total_gulag_lost: gulagLost, 
      gulag_win_ratio: (gulagWins + gulagLost > 0) ? ((gulagWins / (gulagWins + gulagLost)) * 100).toFixed(1) + '%' : 'N/A',
      total_score_from_games: pStat.total_score_from_games || 0
    };
  }).sort((a,b) => b.total_score_from_games - a.total_score_from_games);
});
</script>

<template>
  <div class="mk-detail-view">
    <header class="page-header">
      <img :src="logoWarzone" alt="Warzone Logo" class="warzone-logo">
      <h1 v-if="masterkillEvent">GESTION MK: {{ masterkillEvent.name }}</h1>
      <h1 v-else-if="isLoading && !masterkillEvent">Chargement du MK...</h1>
      <h1 v-else>Événement Masterkill</h1>
    </header>

    <div class="content-wrapper-detail">
      <div v-if="isLoading && !masterkillEvent" class="loading">Chargement des détails...</div>
      <div v-else-if="error" class="error-message">{{ error }}</div>
      <div v-else-if="masterkillEvent" class="mk-details-content">

        <div class="mk-info-header">
          <p>
            <strong>Statut :</strong>
            <span :class="`status-badge status-${masterkillEvent.status}`">{{ masterkillEvent.status }}</span>
            <span v-if="masterkillEvent.status === 'inprogress' && masterkillEvent.num_games_planned > 0" class="current-round-info">
              &nbsp; | &nbsp; Manche {{ completedGamesCountInMK + 1 }} / {{ masterkillEvent.num_games_planned }}
            </span>
          </p>
          <div class="actions-buttons">
            <button v-if="canStartCurrentPendingGame" @click="startFirstGameOrNext" class="action-btn start-btn">
              Démarrer Partie {{ currentDisplayedGameNumber }}
            </button>
            <button v-if="canPauseMK" @click="pauseMK" class="action-btn pause-btn">Pause MK</button>
            <button v-if="canResumeMK" @click="resumeMK" class="action-btn resume-btn">Reprendre MK</button>
          </div>
        </div>
        <hr>

        <h3>Détails Événement</h3>
        <div class="details-grid">
          <p><strong>Créateur:</strong> {{ masterkillEvent.creator_details?.gamertag || masterkillEvent.creator_details?.username ||'N/A' }}</p>
          <p><strong>Créé le:</strong> {{ new Date(masterkillEvent.created_at).toLocaleDateString('fr-FR') }}</p>
          <p v-if="masterkillEvent.status === 'completed'"><strong>Durée du MK:</strong> {{ durationOfMK }}</p>
          <p><strong>Parties Prévues:</strong> {{ masterkillEvent.num_games_planned }}</p>
          <p><strong>Gage:</strong> {{ masterkillEvent.selected_gage_text || 'Aucun' }}</p>
          <p v-if="masterkillEvent.has_bonus_reel !== undefined"><strong>Roue des Bonus :</strong> {{ masterkillEvent.has_bonus_reel ? 'Activée' : 'Désactivée' }}</p>
          <p v-if="masterkillEvent.has_kill_multipliers !== undefined"><strong>Multiplicateurs Kills :</strong> {{ masterkillEvent.has_kill_multipliers ? 'Activés' : 'Désactivés' }}</p>
          <p v-if="masterkillEvent.status === 'completed' && completedGamesCountInMK > 0">
            <strong>Moy. Kills/Partie (Global):</strong> {{ averageKillsPerGameOverall }}
          </p>
        </div>
        <h3>Barème Points</h3>
        <div class="details-grid points-rules">
           <p><strong>Kill:</strong>{{masterkillEvent.points_kill}}</p><p><strong>Réa:</strong>{{masterkillEvent.points_rea}}</p>
           <p><strong>Redéploy:</strong>{{masterkillEvent.points_redeploiement}}</p><p><strong>Goulag:</strong>{{masterkillEvent.points_goulag_win}}</p>
           <p><strong>RQ:</strong>{{masterkillEvent.points_rage_quit}}</p><p><strong>Exéc:</strong>{{masterkillEvent.points_execution}}</p>
           <p><strong>Humilié:</strong>{{masterkillEvent.points_humiliation}}</p>
        </div>
        <p v-if="masterkillEvent.top1_solo_ends_mk"><strong>Option:</strong> Le Top 1 Solo met fin à ce MK.</p>
        <h3>Participants</h3>
        <ul v-if="masterkillEvent.participants_details?.length > 0" class="participants-list-detail">
          <li v-for="player in masterkillEvent.participants_details" :key="player.id" class="participant-tag-detail">{{ player.gamertag }}</li>
        </ul>
        <p v-else>Aucun participant.</p>
        <hr>

        <div v-if="showScoreSummaryTable && masterkillEvent.status !== 'completed'" class="score-summary-interstitial">
          <h3>📊 CLASSEMENT PROVISOIRE (Après Partie {{ completedGamesCountInMK }})</h3>
           <div class="table-responsive">
            <table class="stats-table detailed-summary-table">
                <thead>
                <tr>
                    <th>Opérateur</th>
                    <th>Score&nbsp;Actuel</th>
                    <th>Kills</th>
                    <th>Morts</th>
                    <th>K/D</th>
                    <th>Assists (Info)</th>
                    <th>Réanimations</th>
                    <th>Moy.&nbsp;Kills/P.</th>
                    <th>Goulags&nbsp;G.</th>
                    <th>Goulags&nbsp;P.</th>
                    <th>Ratio&nbsp;Goulag</th>
                </tr>
                </thead>
                <tbody>
                <tr v-for="playerStat in detailedPlayerStats" :key="`summary-stat-${playerStat.id}`">
                    <td>{{ playerStat.gamertag }}</td>
                    <td><strong>{{ playerStat.total_score_from_games }}</strong></td>
                    <td>{{ playerStat.total_kills }}</td>
                    <td>{{ playerStat.total_deaths }}</td>
                    <td>{{ playerStat.kd_ratio }}</td>
                    <td>{{ playerStat.total_assists }}</td>
                    <td>{{ playerStat.total_revives_done }}</td>
                    <td>{{ playerStat.average_kills_per_game }}</td>
                    <td>{{ playerStat.total_gulag_wins }}</td>
                    <td>{{ playerStat.total_gulag_lost }}</td>
                    <td>{{ playerStat.gulag_win_ratio }}</td>
                </tr>
                </tbody>
            </table>
          </div>
          <template v-if="masterkillEvent.status !== 'completed'">
             <hr style="margin-top: 20px; margin-bottom: 20px;">
             <p v-if="masterkillEvent.status === 'inprogress' && activeGame?.status === 'pending'" class="info-message subtle-info">
                 Prêt à démarrer la Partie {{ activeGame.game_number }}. Utilisez le bouton "Démarrer Partie" en haut.
             </p>
              <div v-else-if="showExplicitNextGameButton" class="game-actions">
                <button @click="startFirstGameOrNext" class="action-btn next-game-btn">Démarrer Partie {{ (activeGame.game_number || completedGamesCountInMK) + 1 }}</button>
             </div>
              <p v-else-if="masterkillEvent.status === 'paused'" class="info-message subtle-info">MK en pause. Scores actuels affichés.</p>
          </template>
        </div>

        <div class="current-game-section"
             v-else-if="masterkillEvent.status === 'inprogress' || (masterkillEvent.status === 'paused' && activeGame && activeGame.status === 'inprogress')">
          <h2>
            <span v-if="activeGame && activeGame.status !== 'pending'">Partie {{ activeGame.game_number }}</span>
            <span v-else-if="activeGame && activeGame.status === 'pending'">Prêt pour Partie {{ activeGame.game_number }}</span>
            <span v-else-if="masterkillEvent.status === 'inprogress'">Préparation de la partie suivante...</span>
            <span v-else>MK en pause</span>
            <span v-if="activeGame && activeGame.status !== 'pending'"> / {{ masterkillEvent.num_games_planned }}</span>
            <span v-if="masterkillEvent.status === 'paused' && activeGame?.status === 'inprogress' "> (PARTIE EN PAUSE AVEC MK)</span>
            <span v-else-if="masterkillEvent.status === 'paused'"> (MK EN PAUSE)</span>
            <span v-if="activeGame?.status === 'inprogress'"> (EN COURS)</span>
          </h2>
          
          <div v-if="masterkillEvent.has_kill_multipliers && activeGame && activeGame.kill_multiplier && activeGame.kill_multiplier > 1.0" class="multiplier-active-banner">
            🔥 Multiplicateur de Kills x{{ activeGame.kill_multiplier }} ACTIF pour cette partie ! 🔥
          </div>

          <div v-if="isGameCurrentlyInProgress" class="game-input-section">
            <div class="form-group spawn-input-group">
              <label for="game-spawn-location">Lieu de Spawn de la Partie :</label>
              <select id="game-spawn-location" v-model="gameSpawnLocationInput">
                <option value="">-- Sélectionner Spawn --</option>
                <option v-for="(details, name) in mapLocations" :key="`spawn-opt-${name}`" :value="name">
                  {{ details.name }}
                </option>
                 <option value="Autre">Autre (Préciser si besoin)</option>
              </select>
            </div>
            <table class="stats-table">
              <thead><tr><th>Opérateur</th><th>Kills</th><th>Morts</th><th>Assist. (Info)</th><th>Réa. (Compteur)</th><th>Goulag</th><th>Redéployé (Compteur)</th><th>Rage Quit?</th></tr></thead>
              <tbody>
                <tr v-for="player in masterkillEvent.participants_details" :key="player.id">
                  <td>{{ player.gamertag }}</td>
                  <td class="stat-cell"><button @click="changeStat(player.id, 'kills', -1)" class="stat-btn">-</button><span>{{ currentGameStats[player.id]?.kills || 0 }}</span><button @click="changeStat(player.id, 'kills', 1)" class="stat-btn">+</button></td>
                  <td class="stat-cell"><button @click="changeStat(player.id, 'deaths', -1)" class="stat-btn">-</button><span>{{ currentGameStats[player.id]?.deaths || 0 }}</span><button @click="changeStat(player.id, 'deaths', 1)" class="stat-btn">+</button></td>
                  <td class="stat-cell"><button @click="changeStat(player.id, 'assists', -1)" class="stat-btn">-</button><span>{{ currentGameStats[player.id]?.assists || 0 }}</span><button @click="changeStat(player.id, 'assists', 1)" class="stat-btn">+</button></td>
                  <td class="stat-cell"><span>{{ currentGameStats[player.id]?.revives_done || 0 }}</span></td>
                  <td><select :value="currentGameStats[player.id]?.gulag_status || 'not_played'" @change="updateGulagStatus(player.id, $event.target.value)" class="stat-select"><option v-for="opt in gulagOptions" :key="opt.value" :value="opt.value">{{ opt.text }}</option></select></td>
                  <td>{{ currentGameStats[player.id]?.times_redeployed_by_teammate || 0 }}</td>
                  <td><input type="checkbox" :checked="currentGameStats[player.id]?.rage_quit || false" @change="toggleRageQuit(player.id)" class="stat-checkbox"/></td>
                </tr>
              </tbody>
            </table>
            <div class="action-subsection form-actions-horizontal">
                <div class="action-form-container">
                    <button @click="showRedeployLogForm = !showRedeployLogForm" class="action-btn log-redeploy-btn">
                        {{ showRedeployLogForm ? 'Fermer Log Redéploiement' : 'Logger un Redéploiement' }}
                    </button>
                    <form v-if="showRedeployLogForm" @submit.prevent="logRedeployEvent" class="log-event-form">
                        <h4>Qui a redéployé qui ?</h4>
                        <div class="form-group"><label for="redeployer">Redéployeur:</label><select id="redeployer" v-model="redeployData.redeployer_player_id"><option :value="null">--</option><option v-for="p_ in availablePlayersForRedeploy" :key="`rdplr-${p_.id}`" :value="p_.id">{{ p_.gamertag }}</option></select></div>
                        <div class="form-group"><label for="redeployed">Redéployé:</label><select id="redeployed" v-model="redeployData.redeployed_player_id"><option :value="null">--</option><option v-for="p_ in availablePlayersForRedeploy" :key="`rdpld-${p_.id}`" :value="p_.id">{{ p_.gamertag }}</option></select></div>
                        <button type="submit" class="action-btn submit-log-btn">Valider Redéploiement</button><p v-if="redeployError" class="error-message form-error">{{ redeployError }}</p>
                    </form>
                </div>
                <div class="action-form-container">
                    <button @click="showReviveLogForm = !showReviveLogForm" class="action-btn log-revive-btn">
                      {{ showReviveLogForm ? 'Fermer Log Réanimation' : 'Logger une Réanimation' }}
                    </button>
                    <form v-if="showReviveLogForm" @submit.prevent="logReviveEvent" class="log-event-form">
                        <h4>Qui a réanimé qui ?</h4>
                        <div class="form-group"><label for="reviver">Réanimateur:</label><select id="reviver" v-model="reviveData.reviver_player_id"><option :value="null">--</option><option v-for="p_ in availablePlayersForRedeploy" :key="`rvr-${p_.id}`" :value="p_.id">{{ p_.gamertag }}</option></select></div>
                        <div class="form-group"><label for="revived">Réanimé:</label><select id="revived" v-model="reviveData.revived_player_id"><option :value="null">--</option><option v-for="p_ in availablePlayersForRedeploy" :key="`rvd-${p_.id}`" :value="p_.id">{{ p_.gamertag }}</option></select></div>
                        <button type="submit" class="action-btn submit-log-btn">Valider Réanimation</button><p v-if="reviveError" class="error-message form-error">{{ reviveError }}</p>
                    </form>
                </div>
            </div>
            <div class="game-actions">
              <button @click="handleEndGame" v-if="canEndCurrentGame" class="action-btn end-game-btn">Terminer Partie {{ activeGame?.game_number }}</button>
            </div>
          </div>
          <p v-else-if="masterkillEvent.status === 'paused'" class="info-message">MK EN PAUSE. Cliquez sur "Reprendre MK" en haut.</p>
        </div>
        
        <p v-else-if="masterkillEvent.status === 'pending'" class="start-prompt info-message">
            <span v-if="isLoading && !activeGame">Chargement...</span>
            <span v-else>Cliquez sur "Démarrer Partie {{ currentDisplayedGameNumber }}" pour commencer.</span>
        </p>

        <div v-else-if="masterkillEvent.status === 'completed' || masterkillEvent.status === 'cancelled'">
            <p class="completion-message info-message">
              Événement Masterkill {{ masterkillEvent.status }}.
              <span v-if="masterkillEvent.status === 'completed' && determinedWinnerGamertag !== 'Non déterminé'">
                Vainqueur: <strong>{{ determinedWinnerGamertag }}</strong> !
              </span>
              <span v-else-if="masterkillEvent.status === 'completed'">
                Égalité ou vainqueur non déterminable.
              </span>
            </p>

            <div v-if="masterkillEvent.status === 'completed' && mkAggregatedStats.length > 0" class="completed-mk-visuals">
                <hr>
                <div class="stats-and-map-grid">
                    <div class="detailed-stats-section">
                        <h3>Statistiques Détaillées</h3>
                        <h4>Rapport de Combat Complet</h4>
                        <div class="table-responsive">
                            <table class="stats-table detailed-summary-table">
                                <thead>
                                <tr>
                                    <th>Opérateur</th>
                                    <th>Score&nbsp;Final</th>
                                    <th>Kills</th>
                                    <th>Morts</th>
                                    <th>K/D</th>
                                    <th>Assists (Info)</th>
                                    <th>Réanimations</th>
                                    <th>Moy.&nbsp;Kills/P.</th>
                                    <th>Goulags&nbsp;G.</th>
                                    <th>Goulags&nbsp;P.</th>
                                    <th>Ratio&nbsp;Goulag</th>
                                </tr>
                                </thead>
                                <tbody>
                                <tr v-for="playerStat in detailedPlayerStats" :key="`detail-${playerStat.id}`">
                                    <td>{{ playerStat.gamertag }}</td>
                                    <td><strong>{{ playerStat.total_score_from_games }}</strong></td>
                                    <td>{{ playerStat.total_kills }}</td>
                                    <td>{{ playerStat.total_deaths }}</td>
                                    <td>{{ playerStat.kd_ratio }}</td>
                                    <td>{{ playerStat.total_assists }}</td>
                                    <td>{{ playerStat.total_revives_done }}</td>
                                    <td>{{ playerStat.average_kills_per_game }}</td>
                                    <td>{{ playerStat.total_gulag_wins }}</td>
                                    <td>{{ playerStat.total_gulag_lost }}</td>
                                    <td>{{ playerStat.gulag_win_ratio }}</td>
                                </tr>
                                </tbody>
                            </table>
                        </div>
                    </div>
                    
                    <div class="map-section-container">
                        <h3>Carte des Spawns</h3>
                         <div class="location-selector-mk-detail">
                            <label for="location-select-detail">Lieu d'intérêt :</label>
                            <select id="location-select-detail" v-model="selectedMapLocation">
                            <option :value="null">-- Aucun Lieu --</option>
                            <option v-for="(details, name) in mapLocations" :key="name" :value="name">
                                {{ details.name }}
                            </option>
                            </select>
                        </div>
                        <div class="map-container-mk-detail">
                            <img :src="mapWarzoneImage" alt="Carte Warzone" class="map-background-image-detail">
                             <div
                              v-if="selectedMapLocation && mapLocations[selectedMapLocation]"
                              class="map-point-detail selected-spawn-point"
                              :style="{ 
                                left: mapLocations[selectedMapLocation].x + '%', 
                                top: mapLocations[selectedMapLocation].y + '%' 
                              }"
                              :title="mapLocations[selectedMapLocation].name"
                            >★</div>
                            <div v-for="(game, index) in masterkillEvent.games.filter(g => g.status === 'completed' && g.spawn_location && mapLocations[g.spawn_location])" 
                                :key="`spawn-point-${game.id || index}`"
                                class="map-point-detail game-spawn-point"
                                :style="{ left: mapLocations[game.spawn_location].x + '%', top: mapLocations[game.spawn_location].y + '%' }"
                                :title="`${mapLocations[game.spawn_location].name} (Partie ${game.game_number})`"
                            >{{ game.game_number }}</div>
                        </div>
                    </div>
                </div>

                <div v-if="chartDatasetsDetail.length > 0 && masterkillEvent.status === 'completed'" class="chart-section-detail">
                    <hr style="margin-top: 30px;">
                    <h3>Évolution des Scores par Partie</h3>
                    <div v-if="isLoadingGraphDataDetail" class="loading">Chargement du graphique...</div>
                    <div v-else class="chart-container-detail">
                        <Line 
                        :data="chartDataDetail" 
                        :options="chartOptionsDetail" 
                        :key="`score-chart-detail-${mkId}`" 
                        ref="chartInstanceDetailRef" 
                        />
                    </div>
                </div>
                 <div v-if="killsBySpawnData.length > 0" class="kills-by-spawn-section">
                    <hr>
                    <h3>☠️ Kills par Lieu de Spawn ☠️</h3>
                    <div class="table-responsive">
                        <table class="stats-table detailed-summary-table">
                        <thead>
                            <tr>
                            <th>Lieu de Spawn</th>
                            <th>Total Kills Effectués</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr v-for="spawnStat in killsBySpawnData" :key="spawnStat.spawn_location">
                            <td>{{ mapLocations[spawnStat.spawn_location]?.name || spawnStat.spawn_location }}</td>
                            <td><strong>{{ spawnStat.total_kills }}</strong></td>
                            </tr>
                        </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>

        <div class="mk-global-actions">
          <button @click="startFirstGameOrNext" v-if="showExplicitNextGameButton" class="action-btn next-game-btn">
            Démarrer Partie {{ (activeGame?.game_number || completedGamesCountInMK) + 1 }}
          </button>
          <button v-if="canEndMK" @click="endMK" class="action-btn end-mk-btn">Terminer le Masterkill</button>
        </div>
        <RouterLink :to="{ name: 'home' }" class="back-to-list-btn">Retour à la liste</RouterLink>
      </div>
      <p v-else>Aucun détail à afficher.</p>
    </div>
  </div>
</template>

<style scoped>
.stats-table { width: 100%; border-collapse: separate; border-spacing: 0 6px; margin-bottom: 25px; font-size: 0.9em; table-layout: auto; }
.stats-table th, .stats-table td { border-bottom: 1px solid var(--wz-border-color); padding: 10px 5px; text-align: center; vertical-align: middle; }
.stats-table thead th { background-color: transparent; color: var(--wz-accent-cyan); text-transform: uppercase; font-size: 0.8em; border-bottom-width: 2px; padding: 10px 4px; }
.stats-table td:first-child, .stats-table th:first-child { 
  text-align: left; 
  font-weight: bold; 
  color: var(--wz-text-light); 
  font-size: 0.9em;
  padding-left: 10px; 
  min-width: 100px;
  white-space: nowrap;
}
.mk-detail-view { min-height: 100vh; font-family: "Agency FB", "Roboto Condensed", Arial, sans-serif; background-color: var(--wz-bg-dark); background-image: linear-gradient(rgba(16, 16, 16, 0.9), rgba(16, 16, 16, 0.97)), url('@/assets/images/logo-warzone.png'); background-size: cover; background-position: center center; background-attachment: fixed; color: var(--wz-text-light); padding: 20px 0; box-sizing: border-box; }
.page-header { background-color: rgba(0,0,0,0.6); padding: 20px; text-align: center; border-bottom: 3px solid var(--wz-accent-yellow); margin-bottom: 30px; }
.warzone-logo { max-height: 70px; margin-bottom: 15px; }
.page-header h1 { color: var(--wz-text-light); font-size: 1.8em; text-transform: uppercase; letter-spacing: 2px; margin: 0; border-bottom: none; font-weight: 700; }
.content-wrapper-detail { width: 95vw; max-width: 1600px; margin-left: auto; margin-right: auto; background-color: rgba(30, 30, 30, 0.92); padding: 25px 30px; border-radius: 8px; box-shadow: 0 5px 25px rgba(0,0,0,0.7); }
.loading, .error-message { text-align: center; padding: 30px; color: var(--wz-text-medium); font-size: 1.2em;}
.error-message:not(.form-error) { color: var(--wz-text-dark); background-color: var(--wz-accent-red); border: 1px solid #c00; padding: 15px; border-radius: 4px;}
.form-error { color: var(--wz-text-dark); background-color: var(--wz-accent-red); border:1px solid #c00; padding:10px; border-radius:4px; margin-top:10px;}
.mk-info-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; padding-bottom: 15px; border-bottom: 1px solid var(--wz-border-color); flex-wrap: wrap; gap: 10px;}
.mk-info-header p { margin: 0; display: flex; align-items: center; }
.mk-info-header p strong { color: var(--wz-accent-cyan); }
.status-badge { font-size: 0.9em; padding: 6px 12px; border-radius: 15px; color: var(--wz-bg-dark); text-transform: uppercase; font-weight: bold; display: inline-block; vertical-align: middle;}
.status-pending { background-color: var(--wz-accent-yellow); color: var(--wz-text-dark); }
.status-inprogress { background-color: var(--wz-accent-green); color: white; }
.status-paused { background-color: #fd7e14; color: white; }
.status-completed { background-color: #6c757d; color: white; }
.status-cancelled { background-color: #dc3545; color: white; }
.current-round-info { color: var(--wz-text-medium); font-size: 0.95em; margin-left: 10px; display: inline-block; vertical-align: middle; }
.actions-buttons { display: flex; flex-wrap: wrap; gap: 10px; }
.actions-buttons .action-btn { padding: 8px 15px; margin-left: 0; font-size: 0.9em; }
.mk-details-content h3 { color: var(--wz-accent-cyan); margin-top: 25px; margin-bottom: 15px; border-bottom: 1px solid var(--wz-border-color); padding-bottom: 8px; font-size: 1.4em; }
.details-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 8px 15px; margin-bottom: 15px; }
.details-grid p, .mk-details-content > p:not(.info-message):not(.completion-message) { margin-bottom: 6px; color: var(--wz-text-medium); font-size: 0.9em; }
.details-grid p strong, .mk-details-content > p strong { color: var(--wz-text-light); }
.participants-list-detail { list-style: none; padding: 0; display: flex; flex-wrap: wrap; gap: 8px; }
.participant-tag-detail { background-color: var(--wz-bg-light); color: var(--wz-accent-yellow); padding: 5px 10px; border-radius: 4px; font-size: 0.9em; border: 1px solid var(--wz-border-color); }
hr { border: 0; height: 1px; background: var(--wz-border-color); margin: 25px 0; }
.current-game-section { margin-top: 25px; padding: 20px; background-color: rgba(0,0,0,0.3); border: 1px solid var(--wz-border-color); border-radius: 8px; }
.current-game-section h2 { color: var(--wz-accent-yellow); border-bottom: 1px solid var(--wz-border-color); padding-bottom: 10px; margin-bottom: 20px; font-size: 1.5em; }
.multiplier-active-banner { background-color: var(--wz-accent-yellow); color: var(--wz-text-dark); padding: 10px; text-align: center; font-weight: bold; margin-bottom: 15px; border-radius: 4px;}
.game-input-section .form-group { margin-bottom: 15px; display: flex; align-items: center; gap: 10px;}
.game-input-section .form-group label { margin-right: 10px; color: var(--wz-text-medium); white-space: nowrap; }
.game-input-section .form-group select, 
.game-input-section .form-group input[type="text"] {
  padding: 6px 8px; font-size: 0.9em; 
  background-color: var(--wz-bg-dark); 
  color: var(--wz-text-light); 
  border:1px solid var(--wz-border-color); 
  border-radius: 4px;
  flex-grow: 1;
}
.spawn-input-group {
    margin-bottom: 20px;
    padding-bottom: 20px;
    border-bottom: 1px dashed var(--wz-border-color);
}
.stat-cell span { display: inline-block; min-width: 25px; text-align: center; margin: 0 5px; font-weight: bold; font-size: 1.1em; }
.stat-btn { background-color: var(--wz-bg-light); color: var(--wz-text-light); border: 1px solid var(--wz-border-color); padding: 2px 6px; border-radius: 3px; cursor: pointer; font-weight: bold; min-width: 22px; font-size: 1.1em; line-height: 1; }
.stat-btn:hover { opacity: 0.8; background-color: var(--wz-accent-yellow); color: var(--wz-text-dark); }
.stat-checkbox, .stat-select { accent-color: var(--wz-accent-yellow); transform: scale(1.2); cursor: pointer; vertical-align: middle; }
.stat-select { background-color: var(--wz-bg-dark); color: var(--wz-text-light); border: 1px solid var(--wz-border-color); padding: 4px 6px; border-radius: 4px; font-size: 0.9em; transform: scale(1.1); }

.action-subsection { margin-top: 25px; padding-top: 20px; border-top: 1px dashed var(--wz-border-color); display: flex; flex-direction: column; gap: 20px; }
.action-form-container { margin-bottom: 10px; }
.log-redeploy-btn, .log-revive-btn { background-color: var(--wz-accent-cyan); color: var(--wz-text-dark); margin-bottom: 10px; width: fit-content; }
.log-revive-btn { background-color: #fd7e14; } /* Orange pour différencier */
.log-event-form { background-color: var(--wz-bg-light); padding: 20px; border-radius: 5px; border: 1px solid var(--wz-border-color); margin-top: 10px; }
.log-event-form h4 { margin-top: 0; margin-bottom: 15px; color: var(--wz-text-light); font-size: 1.1em; border-bottom: none; }
.log-event-form .form-group { margin-bottom: 15px; display: flex; align-items: center; gap: 10px; }
.log-event-form .form-group label { width: auto; min-width: 100px; text-align: right;}
.log-event-form select { flex-grow: 1; padding: 8px 10px; background-color: var(--wz-bg-dark); color: var(--wz-text-light); border: 1px solid #454545; border-radius: 4px; }
.submit-log-btn { background-color: var(--wz-accent-green); color: white; font-size: 0.9em; padding: 8px 15px; margin-left: auto; margin-top:10px; display: block;}

.game-actions, .mk-global-actions { margin-top: 20px; text-align: center; display: flex; gap: 15px; justify-content: center; flex-wrap: wrap; }
.action-btn { padding: 10px 18px; font-size: 0.95em; text-transform: uppercase; font-weight: bold; letter-spacing: 0.5px; border-radius: 4px; cursor: pointer; transition: all 0.2s ease; border: 1px solid transparent; color: white; }
.info-message, .completion-message { text-align: center; font-style: italic; padding: 15px 20px; background-color: rgba(0,0,0,0.2); border: 1px solid var(--wz-border-color); border-radius: 4px; margin-top: 20px; color: var(--wz-text-medium); font-size: 1.1em;}
.back-to-list-btn { display: inline-block; margin-top: 30px; padding: 10px 20px; background-color: var(--wz-accent-cyan); color: var(--wz-text-dark); text-decoration: none; border-radius: 4px; font-weight: bold; transition: background-color 0.3s ease; }
.back-to-list-btn:hover { background-color: #29deef; }

.completed-mk-visuals { margin-top: 20px; }
.stats-and-map-grid { display: grid; grid-template-columns: minmax(0, 2.5fr) minmax(0, 1fr); gap: 20px; align-items: flex-start; }
@media (max-width: 992px) { .stats-and-map-grid { grid-template-columns: 1fr; } }
.detailed-stats-section h3, .map-section-container h3 { color: var(--wz-accent-yellow); text-align: center; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 20px; }
.detailed-stats-section h4 { color: var(--wz-accent-cyan); font-size: 1.1em; margin-top: 20px; margin-bottom: 10px; }
.table-responsive { overflow-x: auto; background-color: rgba(0,0,0,0.2); padding: 10px; border-radius: 6px; border: 1px solid var(--wz-border-color); }
.detailed-summary-table td, .detailed-summary-table th { padding: 6px 8px; white-space: nowrap; font-size: 0.8em; text-align: center; }
.detailed-summary-table td:first-child, .detailed-summary-table th:first-child { min-width: 100px; text-align: left; position: sticky; left: 0; background-color: var(--wz-bg-medium); z-index: 1; }
.detailed-summary-table th:first-child { z-index: 2; }
.detailed-summary-table strong { font-size: 1.05em; color: var(--wz-text-light); }
.map-section-container { padding:15px; background-color: rgba(0,0,0,0.2); border-radius: 6px; border: 1px solid var(--wz-border-color); }
@media (min-width: 993px) { .map-section-container { position: sticky; top: 80px; } }
.location-selector-mk-detail { width: 100%; text-align: center; margin-bottom: 10px; }
.location-selector-mk-detail label { margin-right: 10px; color: var(--wz-text-medium); }
.location-selector-mk-detail select { padding: 8px 10px; background-color: var(--wz-bg-input); color: var(--wz-text-light); border: 1px solid var(--wz-border-color); border-radius: 4px; min-width: 220px; }
.map-container-mk-detail { position: relative; width: 100%; max-width: 400px; border: 2px solid var(--wz-border-color); border-radius: 4px; overflow: hidden; margin: 0 auto; aspect-ratio: 1 / 1; }
.map-background-image-detail { display: block; width: 100%; height: 100%; object-fit: cover; }
.map-point-detail { position: absolute; width: 10px; height: 10px; background-color: var(--wz-accent-red); border: 1px solid white; border-radius: 50%; transform: translate(-50%, -50%); box-shadow: 0 0 6px black; font-size: 0.7em; display: flex; align-items: center; justify-content: center; color: white; font-weight: bold; z-index: 10; }
.game-spawn-point { background-color: var(--wz-accent-cyan); opacity: 0.8; width:12px; height:12px; }
.selected-spawn-point { background-color: gold; border-color: black; width: 14px; height: 14px; z-index: 11; font-size:1em;}
.chart-section-detail { margin-top: 25px; padding: 15px; background-color: rgba(0,0,0,0.2); border-radius: 6px; border: 1px solid var(--wz-border-color); }
.chart-section-detail h3 { color: var(--wz-accent-yellow); text-align: center; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 20px; }
.chart-container-detail { height: 350px; position: relative; }
.summary-table td:first-child { width: auto; min-width: 50px; text-align: center; padding-left: 5px;}
.summary-table td:nth-child(2) { width: auto; text-align: left; padding-left: 15px;}
.summary-table td:nth-child(3) { width: auto; min-width: 80px; text-align: center; font-size: 1.1em;}

.points-rules p {font-size: 0.9em;}
.start-btn { background-color: var(--wz-accent-green); border-color: var(--wz-accent-green); }
.start-btn:hover { background-color: #34ce57; }
.pause-btn { background-color: var(--wz-accent-yellow); color: var(--wz-text-dark); border-color: var(--wz-accent-yellow);}
.pause-btn:hover { background-color: #ffd040; }
.resume-btn { background-color: var(--wz-accent-cyan); color: var(--wz-text-dark); border-color: var(--wz-accent-cyan);}
.resume-btn:hover { background-color: #29deef; }
.end-game-btn { background-color: var(--wz-accent-red); border-color: var(--wz-accent-red);}
.end-game-btn:hover { background-color: #c82333; }
.next-game-btn { background-color: var(--wz-accent-green); border-color: var(--wz-accent-green);}
.end-mk-btn { background-color: #343a40; border-color: #343a40; }
.end-mk-btn:hover { background-color: #23272b; }
/* Ajustement pour que les boutons de log soient sur la même ligne si possible */
.action-subsection.form-actions-horizontal {
    display: flex;
    flex-direction: row; /* Aligner les conteneurs de formulaire horizontalement */
    gap: 20px; /* Espace entre les formulaires */
    align-items: flex-start; /* Aligner en haut */
    flex-wrap: wrap; /* Permettre le retour à la ligne si pas assez de place */
}
.action-form-container {
    display: flex;
    flex-direction: column; /* Les boutons et formulaires internes restent en colonne */
    gap: 10px; /* Espace entre le bouton et son formulaire */
    flex: 1; /* Permet aux conteneurs de formulaires de se partager l'espace */
    min-width: 300px; /* Largeur minimale pour chaque bloc de formulaire */
}

.log-redeploy-btn, .log-revive-btn { 
    background-color: var(--wz-accent-cyan); 
    color: var(--wz-text-dark); 
    margin-bottom: 0; 
    width: auto; /* S'adapte au contenu */
    align-self: flex-start; /* Aligner le bouton à gauche de son conteneur */
    padding: 8px 15px;
}
.log-revive-btn { 
    background-color: #fd7e14; /* Orange pour différencier */
}
.submit-log-btn { 
    background-color: var(--wz-accent-green); 
    color: white; 
    font-size: 0.9em; 
    padding: 8px 15px; 
    margin-left: 0; /* Retiré */
    margin-top:10px; 
    align-self: flex-start; /* Aligner le bouton à gauche de son conteneur */
}
</style>