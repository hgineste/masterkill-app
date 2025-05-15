<script setup>
import { ref, onMounted, computed, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
// MODIFIÉ: Importer apiClient
import apiClient from '@/services/apiClient'; // Assurez-vous que ce chemin est correct
import logoWarzone from '@/assets/images/logo-warzone.png';

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

const gulagOptions = ref([
  { value: 'not_played', text: 'Non Joué / Fermé' },
  { value: 'won', text: 'Gagné' },
  { value: 'lost', text: 'Perdu' },
]);

watch(activeGame, (newVal, oldVal) => {
  if ((newVal && newVal.id && (newVal.status === 'inprogress' || newVal.status === 'pending')) || (!newVal && oldVal)) {
     if (!oldVal || newVal.id !== oldVal.id || (newVal.status === 'pending' && oldVal.status !== 'pending') || (newVal.status === 'inprogress' && oldVal.status !== 'inprogress') || !newVal ) {
        initializeCurrentGameStats();
     }
  }
}, { deep: true });

// watch(() => masterkillEvent.value?.status, (newStatus, oldStatus) => {
// });

async function fetchAggregatedStats() {
  if (!masterkillEvent.value || masterkillEvent.value.status === 'pending') {
    mkAggregatedStats.value = []; return;
  }
  try {
    // MODIFIÉ: Utiliser apiClient et URL relative
    const response = await apiClient.get(`/masterkillevents/${mkId.value}/aggregated-stats/`);
    mkAggregatedStats.value = response.data || [];
  } catch (err) {
    console.error("Erreur fetch stats agrégées:", err);
    mkAggregatedStats.value = [];
  }
}

async function fetchMKDetails(resetStatsIfNeeded = true) {
  isLoading.value = true; error.value = null;
  let initialActiveGameId = activeGame.value?.id;
  let initialActiveGameStatus = activeGame.value?.status;
  try {
    // MODIFIÉ: Utiliser apiClient et URL relative
    const response = await apiClient.get(`/masterkillevents/${mkId.value}/`);
    masterkillEvent.value = response.data;

    const gameInfoFromServer = masterkillEvent.value.current_game_info;

    if (gameInfoFromServer && (gameInfoFromServer.id || gameInfoFromServer.status === 'pending')) {
      activeGame.value = gameInfoFromServer;
    } else if (masterkillEvent.value.status === 'pending') {
      activeGame.value = { game_number: 1, status: 'pending', id: null, masterkill_event: mkId.value };
    } else if (masterkillEvent.value.status === 'inprogress' && !gameInfoFromServer) {
      const completedGamesCount = masterkillEvent.value.games?.filter(g => g.status === 'completed').length || 0;
      if (completedGamesCount < masterkillEvent.value.num_games_planned) {
        activeGame.value = { game_number: completedGamesCount + 1, status: 'pending', id: null, masterkill_event: mkId.value };
      } else {
        activeGame.value = null;
      }
    } else {
      activeGame.value = null;
    }

    if (masterkillEvent.value.status !== 'pending') {
      await fetchAggregatedStats();
    } else {
      mkAggregatedStats.value = [];
    }

     if (resetStatsIfNeeded) {
       const gameChanged = !activeGame.value || activeGame.value.id !== initialActiveGameId || (activeGame.value.id === initialActiveGameId && activeGame.value.status === 'pending' && initialActiveGameStatus !== 'pending');
       const isNewGameScenario = gameChanged && (activeGame.value?.status !== 'inprogress' || !initialActiveGameId || activeGame.value.id !== initialActiveGameId);
       if (isNewGameScenario) {
           initializeCurrentGameStats();
       }
     }
  } catch (err) {
    error.value = `Impossible de charger détails MK ${mkId.value}.`;
    if (err.response?.status === 404) error.value = `MK ${mkId.value} non trouvé.`;
  } finally { isLoading.value = false; }
}

function initializeCurrentGameStats() {
  if (masterkillEvent.value?.participants_details) {
    const stats = {};
    masterkillEvent.value.participants_details.forEach(player => {
      stats[player.id] = {
        kills: 0, deaths: 0, assists: 0, gulag_status: 'not_played',
        revives_done: 0, times_executed_enemy: 0, times_got_executed: 0,
        rage_quit: false, times_redeployed_by_teammate: 0,
      };
    });
    currentGameStats.value = stats;
  } else {
      currentGameStats.value = {};
  }
}

function changeStat(playerId, statName, delta) {
  if (currentGameStats.value[playerId]?.[statName] !== undefined && typeof currentGameStats.value[playerId][statName] === 'number') {
    const newValue = currentGameStats.value[playerId][statName] + delta;
    currentGameStats.value[playerId][statName] = Math.max(0, newValue);
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
  if (!masterkillEvent.value) return;
  isLoading.value = true;
  try {
    // MODIFIÉ: Utiliser apiClient et URL relative
    const response = await apiClient.post(`/masterkillevents/${mkId.value}/manage_game/`, { action: actionToDo });
    activeGame.value = response.data;
    if (masterkillEvent.value.status === 'pending' && activeGame.value?.status === 'inprogress') {
      masterkillEvent.value.status = 'inprogress';
    }
    await fetchMKDetails(true);
  } catch (err) {
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
    // MODIFIÉ: Utiliser apiClient et URL relative
    await apiClient.patch(`/masterkillevents/${masterkillEvent.value.id}/`, { status: newStatus });
    await fetchMKDetails(newStatus === 'pending');
    if (newStatus === 'completed' && masterkillEvent.value?.status === 'completed') {
      router.push({ name: 'masterkill-results', params: { id: mkId.value } });
    }
  } catch (err) {
    alert(`Erreur màj statut MK: ${err.message}`);
    await fetchMKDetails(false);
  } finally {
    isLoading.value = false;
  }
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
    // MODIFIÉ: Utiliser apiClient et URL relative (endpoint pour redeployevents)
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
  if (!confirm(`Terminer Partie ${activeGame.value.game_number} et enregistrer scores ?`)) return;

  const playerStatsPayloadList = masterkillEvent.value.participants_details.map(player => {
    const stats = currentGameStats.value[player.id] || {};
    return {
      player_id: player.id, kills: stats.kills || 0, deaths: stats.deaths || 0,
      assists: stats.assists || 0, gulag_status: stats.gulag_status || 'not_played',
      revives_done: stats.revives_done || 0, times_executed_enemy: stats.times_executed_enemy || 0,
      times_got_executed: stats.times_got_executed || 0, rage_quit: stats.rage_quit || false,
      times_redeployed_by_teammate: stats.times_redeployed_by_teammate || 0,
    };
  });
  isLoading.value = true;
  try {
    // MODIFIÉ: Utiliser apiClient et URL relative
    const response = await apiClient.post(
      `/games/${activeGame.value.id}/complete/`,
      { player_stats: playerStatsPayloadList }
    );
    alert(response.data.message || "Partie terminée!");

    if (response.data.mk_ended || response.data.mk_status === 'completed') {
      await fetchMKDetails(false); // Re-fetch pour avoir le statut final et le vainqueur
      router.push({ name: 'masterkill-results', params: { id: mkId.value } });
    } else {
      await fetchMKDetails(true);
    }
  } catch (err) {
    alert(`Erreur fin de partie: ${err.response?.data?.error || err.message}`);
    await fetchMKDetails(false);
  } finally {
    isLoading.value = false;
  }
}

onMounted(() => { fetchMKDetails(); });

const canStartCurrentPendingGame = computed(() => masterkillEvent.value && (masterkillEvent.value.status === 'pending' || masterkillEvent.value.status === 'inprogress') && activeGame.value?.status === 'pending');
const canPauseMK = computed(() => masterkillEvent.value?.status === 'inprogress' && activeGame.value?.status === 'inprogress');
const canResumeMK = computed(() => masterkillEvent.value?.status === 'paused');
const isGameCurrentlyInProgress = computed(() => masterkillEvent.value?.status === 'inprogress' && activeGame.value?.status === 'inprogress');
const canEndCurrentGame = computed(() => isGameCurrentlyInProgress.value && activeGame.value?.id );
const showExplicitNextGameButton = computed(() => {
    if (!masterkillEvent.value || !activeGame.value) return false;
    return masterkillEvent.value.status === 'inprogress' &&
           activeGame.value.status === 'completed' &&
           activeGame.value.game_number < masterkillEvent.value.num_games_planned;
});

const canEndMK = computed(() => {
  return masterkillEvent.value &&
         (masterkillEvent.value.status === 'inprogress' || masterkillEvent.value.status === 'paused');
});

const availablePlayersForRedeploy = computed(() => masterkillEvent.value?.participants_details || []);
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
           masterkillEvent.value.status === 'completed' ||
           (masterkillEvent.value.status === 'inprogress' && activeGame.value?.status === 'completed') ||
           (masterkillEvent.value.status === 'inprogress' && activeGame.value?.status === 'pending' && completedGamesCountInMK.value > 0)
         );
});

const rankedPlayerScoresSoFar = computed(() => {
  if (!mkAggregatedStats.value || mkAggregatedStats.value.length === 0) return [];
  return [...mkAggregatedStats.value]
    .sort((a, b) => (b.total_score_from_games || 0) - (a.total_score_from_games || 0))
    .map((pStat, index) => ({
      rank: index + 1, gamertag: pStat.player.gamertag,
      totalScore: pStat.total_score_from_games || 0, playerId: pStat.player.id
    }));
});

const determinedWinnerGamertag = computed(() => {
  if (masterkillEvent.value?.winner_details?.gamertag) {
    return masterkillEvent.value.winner_details.gamertag;
  }
  if (masterkillEvent.value?.status === 'completed' && rankedPlayerScoresSoFar.value.length > 0) {
    return rankedPlayerScoresSoFar.value[0].gamertag;
  }
  return 'Non déterminé';
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
          <p><strong>Créateur:</strong> {{ masterkillEvent.creator_details?.gamertag || 'N/A' }}</p>
          <p><strong>Créé le:</strong> {{ new Date(masterkillEvent.created_at).toLocaleDateString('fr-FR') }}</p>
          <p><strong>Parties Prévues:</strong> {{ masterkillEvent.num_games_planned }}</p>
          <p><strong>Gage:</strong> {{ masterkillEvent.selected_gage_text || 'Aucun' }}</p>
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

        <div v-if="showScoreSummaryTable" class="score-summary-interstitial">
          <h3 v-if="masterkillEvent.status === 'completed'">📊 CLASSEMENT FINAL</h3>
          <h3 v-else>📊 CLASSEMENT PROVISOIRE (Après Partie {{ completedGamesCountInMK }})</h3>
          <table class="stats-table summary-table">
             <thead><tr><th>Rang</th><th>Opérateur</th><th>Score Total</th></tr></thead>
             <tbody>
               <tr v-for="playerScore in rankedPlayerScoresSoFar" :key="playerScore.playerId">
                 <td>#{{ playerScore.rank }}</td><td>{{ playerScore.gamertag }}</td><td><strong>{{ playerScore.totalScore }}</strong></td>
               </tr>
             </tbody>
          </table>
          <template v-if="masterkillEvent.status !== 'completed'">
             <hr style="margin-top: 20px; margin-bottom: 20px;">
             <p v-if="masterkillEvent.status === 'inprogress' && activeGame?.status === 'pending'" class="info-message subtle-info">
                 Prêt à démarrer la Partie {{ activeGame.game_number }}. Utilisez le bouton "Démarrer Partie" en haut.
             </p>
              <div v-else-if="showExplicitNextGameButton" class="game-actions">
                <button @click="startFirstGameOrNext" class="action-btn next-game-btn">Démarrer Partie {{ (activeGame.game_number || 0) + 1 }}</button>
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

          <div v-if="isGameCurrentlyInProgress">
            <table class="stats-table">
              <thead><tr><th>Opérateur</th><th>Kills</th><th>Morts</th><th>Assist.</th><th>Réa. Done</th><th>Goulag</th><th>Redéployé</th><th>Rage Quit?</th></tr></thead>
              <tbody>
                <tr v-for="player in masterkillEvent.participants_details" :key="player.id">
                  <td>{{ player.gamertag }}</td>
                  <td class="stat-cell"><button @click="changeStat(player.id, 'kills', -1)" class="stat-btn">-</button><span>{{ currentGameStats[player.id]?.kills || 0 }}</span><button @click="changeStat(player.id, 'kills', 1)" class="stat-btn">+</button></td>
                  <td class="stat-cell"><button @click="changeStat(player.id, 'deaths', -1)" class="stat-btn">-</button><span>{{ currentGameStats[player.id]?.deaths || 0 }}</span><button @click="changeStat(player.id, 'deaths', 1)" class="stat-btn">+</button></td>
                  <td class="stat-cell"><button @click="changeStat(player.id, 'assists', -1)" class="stat-btn">-</button><span>{{ currentGameStats[player.id]?.assists || 0 }}</span><button @click="changeStat(player.id, 'assists', 1)" class="stat-btn">+</button></td>
                  <td class="stat-cell"><button @click="changeStat(player.id, 'revives_done', -1)" class="stat-btn">-</button><span>{{ currentGameStats[player.id]?.revives_done || 0 }}</span><button @click="changeStat(player.id, 'revives_done', 1)" class="stat-btn">+</button></td>
                  <td><select :value="currentGameStats[player.id]?.gulag_status || 'not_played'" @change="updateGulagStatus(player.id, $event.target.value)" class="stat-select"><option v-for="opt in gulagOptions" :key="opt.value" :value="opt.value">{{ opt.text }}</option></select></td>
                  <td>{{ currentGameStats[player.id]?.times_redeployed_by_teammate || 0 }}</td>
                  <td><input type="checkbox" :checked="currentGameStats[player.id]?.rage_quit || false" @change="toggleRageQuit(player.id)" class="stat-checkbox"/></td>
                </tr>
              </tbody>
            </table>
            <div class="action-subsection">
                <button @click="showRedeployLogForm = !showRedeployLogForm" class="action-btn log-redeploy-btn">{{ showRedeployLogForm ? 'Fermer Log Redéploiement' : 'Logger un Redéploiement' }}</button>
                <form v-if="showRedeployLogForm" @submit.prevent="logRedeployEvent" class="log-event-form">
                    <h4>Qui a redéployé qui ?</h4>
                    <div class="form-group"><label for="redeployer">Redéployeur:</label><select id="redeployer" v-model="redeployData.redeployer_player_id"><option :value="null">--</option><option v-for="p_ in availablePlayersForRedeploy" :key="p_.id" :value="p_.id">{{ p_.gamertag }}</option></select></div>
                    <div class="form-group"><label for="redeployed">Redéployé:</label><select id="redeployed" v-model="redeployData.redeployed_player_id"><option :value="null">--</option><option v-for="p_ in availablePlayersForRedeploy" :key="p_.id" :value="p_.id">{{ p_.gamertag }}</option></select></div>
                    <button type="submit" class="action-btn submit-log-btn">Valider</button><p v-if="redeployError" class="error-message form-error">{{ redeployError }}</p>
                </form>
            </div>
            <div class="game-actions">
              <button @click="handleEndGame" v-if="canEndCurrentGame" class="action-btn end-game-btn">Terminer Partie {{ activeGame?.game_number }}</button>
            </div>
          </div>
          <p v-else-if="masterkillEvent.status === 'paused'" class="info-message">MK EN PAUSE. Cliquez sur "Reprendre MK" en haut.</p>
        </div>

        <p v-else-if="masterkillEvent?.status === 'pending'" class="start-prompt info-message">
            <span v-if="isLoading && !activeGame">Chargement...</span>
            <span v-else>Cliquez sur "Démarrer Partie {{ currentDisplayedGameNumber }}" pour commencer.</span>
         </p>

        <p v-else-if="masterkillEvent && (masterkillEvent.status === 'completed' || masterkillEvent.status === 'cancelled')" class="completion-message info-message">
          Événement Masterkill {{ masterkillEvent.status }}.
          <span>Vainqueur: {{ determinedWinnerGamertag }}!</span>
        </p>


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
/* Styles */
.stats-table {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0 6px;
  margin-bottom: 25px;
  font-size: 0.9em;
  table-layout: fixed;
}

.stats-table th,
.stats-table td {
  border-bottom: 1px solid var(--wz-border-color);
  padding: 10px 5px;
  text-align: center;
  vertical-align: middle;
  overflow: hidden;
  word-break: break-word;
}

.stats-table thead th {
  background-color: transparent;
  color: var(--wz-accent-cyan);
  text-transform: uppercase;
  font-size: 0.85em;
  border-bottom-width: 2px;
  padding: 10px 4px;
}

.stats-table th:first-child,
.stats-table td:first-child {
  text-align: left;
  font-weight: bold;
  color: var(--wz-text-light);
  font-size: 1em;
  padding-left: 10px;
  width: 25%;
}

.mk-detail-view {
  min-height: 100vh;
  font-family: "Agency FB", "Roboto Condensed", Arial, sans-serif;
  background-color: var(--wz-bg-dark);
  background-image: linear-gradient(rgba(16, 16, 16, 0.9), rgba(16, 16, 16, 0.97)), url('@/assets/images/map-background.jpg');
  background-size: cover; background-position: center center; background-attachment: fixed;
  color: var(--wz-text-light);
  padding: 20px 0;
  box-sizing: border-box;
}
.page-header {
  background-color: rgba(0,0,0,0.6); padding: 20px; text-align: center;
  border-bottom: 3px solid var(--wz-accent-yellow); margin-bottom: 30px;
}
.warzone-logo { max-height: 70px; margin-bottom: 15px; }
.page-header h1 {
  color: var(--wz-text-light); font-size: 1.8em; text-transform: uppercase;
  letter-spacing: 2px; margin: 0; border-bottom: none; font-weight: 700;
}

.content-wrapper-detail {
  width: 80vw;
  margin-left: auto;
  margin-right: auto;
  background-color: rgba(30, 30, 30, 0.92);
  padding: 25px 30px;
  border-radius: 8px;
  box-shadow: 0 5px 25px rgba(0,0,0,0.7);
}


.loading, .error-message { text-align: center; padding: 30px; color: var(--wz-text-medium); font-size: 1.2em;}
.error-message:not(.form-error) { color: var(--wz-text-dark); background-color: var(--wz-accent-red); border: 1px solid #c00; padding: 15px; border-radius: 4px;}
.form-error { color: var(--wz-text-dark); background-color: var(--wz-accent-red); border:1px solid #c00; padding:10px; border-radius:4px; margin-top:10px;}
.mk-info-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; padding-bottom: 15px; border-bottom: 1px solid var(--wz-border-color); }
.mk-info-header p { margin: 0; display: flex; align-items: center; } /* Use flex for alignment */
.mk-info-header p strong { color: var(--wz-accent-cyan); }
.status-badge { font-size: 0.9em; padding: 6px 12px; border-radius: 15px; color: var(--wz-bg-dark); text-transform: uppercase; font-weight: bold; display: inline-block; vertical-align: middle;}
.status-pending { background-color: var(--wz-accent-yellow); color: var(--wz-text-dark); }
.status-inprogress { background-color: var(--wz-accent-green); color: white; }
.status-paused { background-color: #fd7e14; color: white; }
.status-completed { background-color: #6c757d; color: white; }
.status-cancelled { background-color: #dc3545; color: white; }
.current-round-info { /* Style for "Manche X / Y" */
  color: var(--wz-text-medium);
  font-size: 0.95em;
  margin-left: 10px;
  display: inline-block;
  vertical-align: middle;
}
.actions-buttons .action-btn { padding: 8px 15px; margin-left: 10px; font-size: 0.9em; text-transform: uppercase; font-weight: bold; letter-spacing: 0.5px; border-radius: 4px; cursor: pointer; transition: all 0.2s ease; border: 1px solid transparent; color: white;}
.start-btn { background-color: var(--wz-accent-green); border-color: var(--wz-accent-green); }
.start-btn:hover { background-color: #34ce57; }
.pause-btn { background-color: var(--wz-accent-yellow); color: var(--wz-text-dark); border-color: var(--wz-accent-yellow);}
.pause-btn:hover { background-color: #ffd040; }
.resume-btn { background-color: var(--wz-accent-cyan); color: var(--wz-text-dark); border-color: var(--wz-accent-cyan);}
.resume-btn:hover { background-color: #29deef; }
.mk-details-content h3 { color: var(--wz-accent-cyan); margin-top: 25px; margin-bottom: 15px; border-bottom: 1px solid var(--wz-border-color); padding-bottom: 8px; font-size: 1.4em; }
.details-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 8px 15px; margin-bottom: 15px; }
.details-grid p, .mk-details-content > p:not(.info-message):not(.completion-message) { margin-bottom: 8px; color: var(--wz-text-medium); font-size: 0.95em; }
.details-grid p strong, .mk-details-content > p strong { color: var(--wz-text-light); }
.points-rules p { font-size: 0.9em; }
.participants-list-detail { list-style: none; padding: 0; display: flex; flex-wrap: wrap; gap: 8px; }
.participant-tag-detail { background-color: var(--wz-bg-light); color: var(--wz-accent-yellow); padding: 5px 10px; border-radius: 4px; font-size: 0.9em; border: 1px solid var(--wz-border-color); }
hr { border: 0; height: 1px; background: var(--wz-border-color); margin: 25px 0; }
.current-game-section { margin-top: 25px; padding: 20px; background-color: rgba(0,0,0,0.3); border: 1px solid var(--wz-border-color); border-radius: 8px; }
.current-game-section h2 { color: var(--wz-accent-yellow); border-bottom: 1px solid var(--wz-border-color); padding-bottom: 10px; margin-bottom: 20px; font-size: 1.5em; }

.stats-table th.stat-cell, .stats-table td.stat-cell {
  padding: 6px 4px;
}
.stat-cell span {
    display: inline-block;
    min-width: 25px;
    text-align: center;
    margin: 0 5px;
    font-weight: bold;
    font-size: 1.1em;
}
.stat-btn { background-color: var(--wz-bg-light); color: var(--wz-text-light); border: 1px solid var(--wz-border-color); padding: 2px 6px; border-radius: 3px; cursor: pointer; font-weight: bold; min-width: 22px; font-size: 1.1em; line-height: 1; }
.stat-btn:hover { opacity: 0.8; background-color: var(--wz-accent-yellow); color: var(--wz-text-dark); }
.stat-checkbox, .stat-select { accent-color: var(--wz-accent-yellow); transform: scale(1.2); cursor: pointer; vertical-align: middle; }
.stat-select { background-color: var(--wz-bg-dark); color: var(--wz-text-light); border: 1px solid var(--wz-border-color); padding: 4px 6px; border-radius: 4px; font-size: 0.9em; transform: scale(1.1); }
.action-subsection { margin-top: 25px; padding-top: 20px; border-top: 1px dashed var(--wz-border-color); }
.log-redeploy-btn { background-color: var(--wz-accent-cyan); color: var(--wz-text-dark); margin-bottom: 15px; }
.log-event-form { background-color: var(--wz-bg-light); padding: 20px; border-radius: 5px; border: 1px solid var(--wz-border-color); }
.log-event-form h4 { margin-top: 0; margin-bottom: 15px; color: var(--wz-text-light); font-size: 1.1em; border-bottom: none; }
.log-event-form .form-group { margin-bottom: 15px; display: flex; align-items: center; gap: 10px; }
.log-event-form .form-group label { width: 90px; text-align: right;}
.log-event-form select { flex-grow: 1; padding: 8px 10px; background-color: var(--wz-bg-dark); color: var(--wz-text-light); border: 1px solid #454545; border-radius: 4px; }
.submit-log-btn { background-color: var(--wz-accent-green); color: white; font-size: 0.9em; padding: 8px 15px; margin-left: 100px; }
.game-actions, .mk-global-actions { margin-top: 20px; text-align: center; display: flex; gap: 15px; justify-content: center; flex-wrap: wrap; }
.action-btn { padding: 10px 18px; font-size: 0.95em; text-transform: uppercase; font-weight: bold; letter-spacing: 0.5px; border-radius: 4px; cursor: pointer; transition: all 0.2s ease; border: 1px solid transparent; color: white;}
.end-game-btn { background-color: var(--wz-accent-red); border-color: var(--wz-accent-red);}
.end-game-btn:hover { background-color: #c82333; }
.next-game-btn { background-color: var(--wz-accent-green); border-color: var(--wz-accent-green);}
.end-mk-btn { background-color: #343a40; border-color: #343a40; }
.end-mk-btn:hover { background-color: #23272b; }
.info-message, .completion-message { text-align: center; font-style: italic; padding: 15px 20px; background-color: rgba(0,0,0,0.2); border: 1px solid var(--wz-border-color); border-radius: 4px; margin-top: 20px; color: var(--wz-text-medium); font-size: 1.1em;}
.subtle-info { background-color: transparent; border: none; font-style: normal; color: var(--wz-text-medium); font-size: 1em;}
.score-summary-interstitial { margin-top: 25px; }
.summary-table td:first-child { width: 15%; text-align: center; padding-left: 5px;} /* Rank */
.summary-table td:nth-child(2) { width: 55%; text-align: left; padding-left: 15px;} /* Gamertag */
.summary-table td:nth-child(3) { width: 30%; text-align: center; font-size: 1.1em;} /* Score */
.back-to-list-btn { display: inline-block; margin-top: 30px; padding: 10px 20px; background-color: var(--wz-accent-cyan); color: var(--wz-text-dark); text-decoration: none; border-radius: 4px; font-weight: bold; transition: background-color 0.3s ease; }
.back-to-list-btn:hover { background-color: #29deef; }

</style>