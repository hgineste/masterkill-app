<script setup>
import { ref, onMounted, computed } from 'vue';
// MODIFIÉ: Importer apiClient au lieu d'axios directement
import apiClient from '@/services/apiClient'; // Assurez-vous que ce chemin est correct
import { RouterLink } from 'vue-router'; // RouterLink est pour le template, pas directement utilisé dans ce script setup pour les appels API
import logoWarzone from '@/assets/images/logo-warzone.png';

const allMasterkillEvents = ref([]);
const isLoading = ref(true);
const error = ref(null);
const activeTab = ref('active');

async function fetchMasterkillEvents() {
  isLoading.value = true;
  error.value = null;
  try {
    // NOTE API (toujours valide) : Le backend doit fournir les champs nécessaires.
    // MODIFIÉ: Utiliser apiClient et une URL relative
    const response = await apiClient.get('/masterkillevents/');
    allMasterkillEvents.value = response.data;
  } catch (err) {
    console.error("Erreur chargement liste MK:", err);
    error.value = "Impossible de charger les Événements Masterkill.";
  } finally {
    isLoading.value = false;
  }
}

const activeMKs = computed(() => {
  return allMasterkillEvents.value
    .filter(mk => ['pending', 'inprogress', 'paused'].includes(mk.status))
    .sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
});

const completedMKs = computed(() => {
  return allMasterkillEvents.value
    .filter(mk => ['completed', 'cancelled'].includes(mk.status))
    .sort((a, b) => new Date(b.ended_at || b.created_at) - new Date(a.ended_at || a.created_at));
});

onMounted(() => {
  fetchMasterkillEvents();
});

function formatDate(dateString) {
    if (!dateString) return 'N/A';
    try {
        return new Date(dateString).toLocaleDateString('fr-FR');
    } catch (e) {
        return 'Date invalide';
    }
}
</script>

<template>
  <div class="masterkill-list-view">
    <header class="page-header">
      <img :src="logoWarzone" alt="Warzone Logo" class="warzone-logo">
      <h1>SITUATION DES ÉVÉNEMENTS MASTERKILL</h1>
    </header>
    <div class="content-wrapper-list">
      <div class="main-content-list">
        <RouterLink :to="{ name: 'create-masterkill' }" class="action-button create-new-mk-button">
          <span class="icon-plus">+</span> Initialiser un Nouvel Événement MK
        </RouterLink>

        <div class="tabs">
          <button @click="activeTab = 'active'" :class="{ 'active-tab': activeTab === 'active' }">
            MK Actifs / En Attente
          </button>
          <button @click="activeTab = 'history'" :class="{ 'active-tab': activeTab === 'history' }">
            Historique des MK
          </button>
        </div>

        <div v-if="activeTab === 'active'">
          <h3 class="list-title"><span class="icon-list">⚡</span> MK Actifs / En Attente</h3>
          <div v-if="isLoading" class="loading">Analyse des données...</div>
          <div v-else-if="error" class="error-message">{{ error }}</div>
          <ul v-else-if="activeMKs.length > 0" class="mk-list">
            <li v-for="mk in activeMKs" :key="mk.id" class="mk-item">
              <RouterLink :to="{ name: 'masterkill-detail', params: { id: mk.id } }" class="mk-item-link">
                <h2>
                  {{ mk.name }}
                  <span v-if="mk.status === 'inprogress' && mk.num_games_planned > 0" class="current-round-info-list">
                    (Manche {{ (mk.completed_games_count ?? 0) + 1 }}/{{ mk.num_games_planned }})
                  </span>
                  <span :class="`mk-status-badge status-${mk.status}`">{{ mk.status }}</span>
                </h2>
              </RouterLink>
              <p><strong>Créateur:</strong> {{ mk.creator_details?.gamertag || mk.creator_details?.username || 'N/A' }} | <strong>Date:</strong> {{ formatDate(mk.created_at) }}</p>
              <p><strong>Gage:</strong> {{ mk.selected_gage_text || 'Aucun' }}</p>
              <div><strong>Opérateurs:</strong>
                <span v-if="mk.participants_details && mk.participants_details.length > 0" class="participants-list">
                  <span v-for="p in mk.participants_details" :key="p.id" class="participant-tag">{{ p.gamertag }}</span>
                </span>
                <span v-else> Non spécifiés</span>
              </div>
            </li>
          </ul>
          <p v-else class="no-gages">Aucun Masterkill actif ou en attente.</p>
        </div>

        <div v-if="activeTab === 'history'">
          <h3 class="list-title"><span class="icon-list">📖</span> Historique des MK</h3>
          <div v-if="isLoading" class="loading">Analyse des données...</div>
          <div v-else-if="error" class="error-message">{{ error }}</div>
          <ul v-else-if="completedMKs.length > 0" class="mk-list">
            <li v-for="mk in completedMKs" :key="mk.id" class="mk-item completed-mk">
              <RouterLink :to="{ name: 'masterkill-detail', params: { id: mk.id } }" class="mk-item-link">
                   <h2>
                     {{ mk.name }}
                     <span :class="`mk-status-badge status-${mk.status}`">{{ mk.status }}</span>
                   </h2>
              </RouterLink>
              <p><strong>Terminé le:</strong> {{ formatDate(mk.ended_at || mk.created_at) }}</p>
              <p class="winner-info" v-if="mk.winner_details?.gamertag"><strong>🏆 Vainqueur : {{ mk.winner_details.gamertag }} 🏆</strong></p>
              <p v-else-if="mk.status === 'completed'"><strong>Vainqueur :</strong> Non déterminé</p>
               <div><strong>Opérateurs:</strong>
                <span v-if="mk.participants_details && mk.participants_details.length > 0" class="participants-list">
                  <span v-for="p in mk.participants_details" :key="p.id" class="participant-tag">{{ p.gamertag }}</span>
                </span>
                <span v-else> Non spécifiés</span>
              </div>
            </li>
          </ul>
          <p v-else class="no-gages">Aucun Masterkill dans l'historique.</p>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.masterkill-list-view { min-height: calc(100vh - 120px); font-family: "Agency FB", "Roboto Condensed", Arial, sans-serif; background-color: var(--wz-bg-dark); background-image: linear-gradient(rgba(16, 16, 16, 0.88), rgba(16, 16, 16, 0.96)), url('@/assets/images/logo-warzone.png'); background-size: cover; background-position: center center; background-attachment: fixed; color: var(--wz-text-light); padding-bottom: 20px;}
.page-header { background-color: rgba(0,0,0,0.6); padding: 20px; text-align: center; border-bottom: 3px solid var(--wz-accent-yellow); margin-bottom: 30px;}
.warzone-logo { max-height: 70px; margin-bottom: 15px; }
.page-header h1 { color: var(--wz-text-light); font-size: 2.2em; text-transform: uppercase; letter-spacing: 3px; margin: 0; border-bottom: none; font-weight: 700;}
.main-content-list { background-color: rgba(30, 30, 30, 0.9); padding: 30px; border-radius: 8px; box-shadow: 0 5px 25px rgba(0,0,0,0.7);}
.content-wrapper-list {
  width: 80vw;
  margin-left: auto;
  margin-right: auto;
  background-color: rgba(30, 30, 30, 0.92);
  padding: 25px 30px;
  border-radius: 8px;
  box-shadow: 0 5px 25px rgba(0,0,0,0.7);
}

.action-button { display: inline-flex; align-items: center; justify-content: center; gap: 10px; color: var(--wz-text-dark); padding: 12px 22px; border: none; border-radius: 5px; cursor: pointer; margin-bottom: 25px; font-size: 1.1em; text-transform: uppercase; font-weight: bold; letter-spacing: 1.2px; transition: all 0.2s ease-in-out; text-decoration: none; box-shadow: 0 3px 7px rgba(0,0,0,0.4);}
.create-new-mk-button { background-color: var(--wz-accent-yellow); color: var(--wz-text-dark); }
.create-new-mk-button:hover { background-color: #ffcf40; transform: translateY(-2px); box-shadow: 0 5px 10px rgba(0,0,0,0.5); }

.tabs { display: flex; margin-bottom: 25px; border-bottom: 2px solid var(--wz-border-color); }
.tabs button { padding: 10px 20px; cursor: pointer; background-color: transparent; border: none; color: var(--wz-text-medium); font-size: 1.1em; font-weight: bold; text-transform: uppercase; letter-spacing: 1px; transition: color 0.3s, border-bottom-color 0.3s; border-bottom: 3px solid transparent; margin-bottom: -2px; }
.tabs button:hover { color: var(--wz-text-light); }
.tabs button.active-tab { color: var(--wz-accent-yellow); border-bottom-color: var(--wz-accent-yellow); }

.list-title { display: flex; align-items: center; font-size: 1.6em; margin-top: 20px; margin-bottom: 25px; color: var(--wz-accent-cyan); border-bottom: 1px solid var(--wz-border-color); padding-bottom: 10px;}
.icon-plus, .icon-list { font-weight: bold; font-size: 1.2em; margin-right: 10px; }
.loading, .no-gages { text-align: center; padding: 25px; color: var(--wz-text-medium); font-size: 1.1em;}
.error-message { color: var(--wz-text-dark); background-color: var(--wz-accent-red); border: 1px solid #c00; padding: 15px; margin-top: 15px; border-radius: 4px; text-align: center; font-weight: bold; }
.mk-list { list-style: none; padding: 0; }
.mk-item-link { text-decoration: none; color: inherit; display: block; }
.mk-item { margin-bottom: 25px; padding: 20px 25px; border: 1px solid var(--wz-border-color); border-left: 6px solid var(--wz-accent-yellow); border-radius: 0 8px 8px 0; background-color: var(--wz-bg-medium); transition: transform 0.2s ease-in-out, border-left-color 0.2s ease-in-out, background-color 0.2s ease; box-shadow: 0 2px 8px rgba(0,0,0,0.3); }
.mk-item:hover { transform: scale(1.02); border-left-color: var(--wz-accent-cyan); background-color: var(--wz-bg-light); }
.mk-item.completed-mk { border-left-color: var(--wz-text-medium); }
.mk-item.completed-mk:hover { border-left-color: var(--wz-accent-green); }
.winner-info { font-weight: bold; color: var(--wz-accent-green) !important; font-size: 1.1em; text-align: center; padding: 5px; background-color: rgba(76, 175, 80, 0.15); border-radius: 4px; margin-top:10px;}
.mk-item h2 {
  margin-top: 0;
  color: var(--wz-text-light);
  margin-bottom: 15px;
  font-size: 1.5em;
  display: flex;
  justify-content: flex-start;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
  border-bottom: 1px dashed var(--wz-border-color);
  padding-bottom: 10px;
}
.current-round-info-list {
  font-size: 0.7em;
  font-weight: normal;
  color: var(--wz-text-medium);
  order: 2;
  white-space: nowrap;
}
.mk-status-badge {
  font-size: 0.75em;
  padding: 5px 10px;
  border-radius: 15px;
  color: var(--wz-bg-dark);
  text-transform: uppercase;
  font-weight: bold;
  letter-spacing: 0.5px;
  order: 3;
  margin-left: auto;
}
.status-pending { background-color: var(--wz-accent-yellow); color: var(--wz-text-dark); }
.status-inprogress { background-color: var(--wz-accent-green); color: white; }
.status-paused { background-color: #fd7e14; color: white; }
.status-completed { background-color: #6c757d; color: white; }
.status-cancelled { background-color: #dc3545; color: white; }

.mk-item p { margin-bottom: 10px; color: var(--wz-text-medium); line-height: 1.7; }
.mk-item p strong { color: var(--wz-text-light); }
.participants-list { margin-left: 8px; display: inline-flex; flex-wrap: wrap; gap: 6px; vertical-align: middle;}
.participant-tag { background-color: var(--wz-bg-light); color: var(--wz-accent-yellow); padding: 4px 8px; border-radius: 4px; margin-right: 6px; font-size: 0.9em; display: inline-block; margin-bottom: 4px; border: 1px solid var(--wz-border-color); }
</style>