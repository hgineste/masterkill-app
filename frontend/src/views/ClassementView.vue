<script setup>
import { ref, onMounted } from 'vue';
// MODIFIÉ: Importer apiClient
import apiClient from '@/services/apiClient'; // Assurez-vous que le chemin est correct
import logoWarzone from '@/assets/images/logo-warzone.png'; // Si utilisé dans le template de cette vue

const allRankingsData = ref({});
const isLoading = ref(true);
const error = ref(null);
const statsList = ref([
    { key: 'total_score', label: 'Score' },
    { key: 'total_kills', label: 'Kills' },
    { key: 'total_deaths', label: 'Morts' },
    { key: 'kd_ratio', label: 'K/D' },
    { key: 'games_played', label: 'Parties' },
    { key: 'mks_won', label: 'MKs' },
    { key: 'total_assists', label: 'Assists' },
    { key: 'total_gulag_wins', label: 'Goulags' },
]);
const sortCriteria = ref({});

async function fetchAllRankings() {
    isLoading.value = true;
    error.value = null;
    try {
        // MODIFIÉ: Utiliser apiClient et une URL relative
        const response = await apiClient.get('/rankings/all-time/');
        const players = response.data;
        const rankingsByStat = {};

        statsList.value.forEach(stat => {
            rankingsByStat[stat.key] = [...players].sort((a, b) => {
                let valA = a[stat.key];
                let valB = b[stat.key];

                if (typeof valA === 'string') valA = valA.toLowerCase();
                if (typeof valB === 'string') valB = valB.toLowerCase();

                let comparison = 0;
                if (valA > valB) comparison = 1;
                else if (valA < valB) comparison = -1;
                
                const defaultDesc = ['total_score', 'total_kills', 'kd_ratio', 'games_played', 'mks_won'].includes(stat.key);
                return defaultDesc ? comparison * -1 : comparison;
            }).map((player, index) => ({ ...player, rank: index + 1 }));
            sortCriteria.value[stat.key] = { sortBy: stat.key, sortDesc: ['total_score', 'total_kills', 'kd_ratio', 'games_played', 'mks_won'].includes(stat.key) };
        });

        allRankingsData.value = rankingsByStat;
    } catch (err) {
        console.error("Erreur fetch classements all-time:", err);
        error.value = "Impossible de charger les classements.";
    } finally {
        isLoading.value = false;
    }
}

function changeSort(statKey) {
    if (!allRankingsData.value[statKey]) return;

    const currentSort = sortCriteria.value[statKey];
    if (currentSort.sortBy === statKey) {
        currentSort.sortDesc = !currentSort.sortDesc;
    } else {
        currentSort.sortBy = statKey;
        currentSort.sortDesc = ['total_score', 'total_kills', 'kd_ratio', 'games_played', 'mks_won'].includes(statKey);
    }

    allRankingsData.value[statKey].sort((a, b) => {
        let valA = a[currentSort.sortBy];
        let valB = b[currentSort.sortBy];

        if (typeof valA === 'string') valA = valA.toLowerCase();
        if (typeof valB === 'string') valB = valB.toLowerCase();

        let comparison = 0;
        if (valA > valB) comparison = 1;
        else if (valA < valB) comparison = -1;

        return currentSort.sortDesc ? comparison * -1 : comparison;
    }).forEach((player, index) => {
        player.rank = index + 1;
    });
}

function getSortIcon(statKey) {
    const currentSort = sortCriteria.value[statKey];
    if (currentSort && currentSort.sortBy === statKey) {
        return currentSort.sortDesc ? '▼' : '▲';
    }
    return ' ';
}

onMounted(() => {
    fetchAllRankings();
});
</script>

<template>
    <div class="classement-view">
        <header class="page-header">
            <img :src="logoWarzone" alt="Warzone Logo" class="warzone-logo">
            <h1>CLASSEMENTS GÉNÉRAUX DES OPÉRATEURS</h1>
        </header>
        <div class="content-wrapper-classement">
            <div v-if="isLoading" class="loading">Chargement des classements...</div>
            <div v-else-if="error" class="error-message">{{ error }}</div>
            <div v-else-if="Object.keys(allRankingsData).length > 0" class="all-rankings-container">
                <div v-for="stat in statsList" :key="stat.key" class="ranking-by-stat">
                    <h2>Classement par {{ stat.label }}</h2>
                    <div class="ranking-table-container">
                        <table class="ranking-table">
                            <thead>
                                <tr>
                                    <th>Rang</th>
                                    <th>Gamertag</th>
                                    <th @click="changeSort(stat.key)" class="sortable" :class="{ active: sortCriteria[stat.key]?.sortBy === stat.key }">
                                        {{ stat.label }} <span class="sort-icon">{{ getSortIcon(stat.key) }}</span>
                                    </th>
                                    </tr>
                            </thead>
                            <tbody>
                                <tr v-for="player in allRankingsData[stat.key]" :key="player.player_id">
                                    <td>#{{ player.rank }}</td>
                                    <td>{{ player.gamertag }}</td>
                                    <td>{{ player[stat.key] }}</td>
                                    </tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
            <p v-else class="no-data">Aucune donnée de classement disponible pour le moment.</p>
        </div>
    </div>
</template>

<style scoped>
/* Styles pour la page de classement modifiée */
.classement-view {
    min-height: 100vh;
    font-family: "Agency FB", "Roboto Condensed", Arial, sans-serif;
    background-color: var(--wz-bg-dark);
    background-image: linear-gradient(rgba(16, 16, 16, 0.88), rgba(16, 16, 16, 0.96)), url('@/assets/images/map-background.jpg');
    background-size: cover;
    background-position: center center;
    background-attachment: fixed;
    color: var(--wz-text-light);
    padding-bottom: 40px;
}

.page-header {
    background-color: rgba(0, 0, 0, 0.6);
    padding: 20px;
    text-align: center;
    border-bottom: 3px solid var(--wz-accent-yellow);
    margin-bottom: 30px;
}

.warzone-logo {
    max-height: 70px;
    margin-bottom: 15px;
}

.page-header h1 {
    color: var(--wz-text-light);
    font-size: 2.2em;
    text-transform: uppercase;
    letter-spacing: 3px;
    margin: 0;
    font-weight: 700;
}


.content-wrapper-classement { 
  width: 80vw; 
  /*max-width: 1300px; 
  min-width: 750px; */
  margin-left: auto;  
  margin-right: auto; 
  background-color: rgba(30, 30, 30, 0.92); 
  padding: 25px 30px; 
  border-radius: 8px; 
  box-shadow: 0 5px 25px rgba(0,0,0,0.7); 
}

.loading,
.no-data,
.error-message {
    text-align: center;
    padding: 30px;
    font-size: 1.2em;
    color: var(--wz-text-medium);
}

.error-message {
    color: var(--wz-text-dark);
    background-color: var(--wz-accent-red);
    border: 1px solid #c00;
}

.all-rankings-container {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
    gap: 30px;
    margin-top: 20px;
}

.ranking-by-stat {
    background-color: var(--wz-bg-medium);
    padding: 20px;
    border-radius: 6px;
    box-shadow: 0 2px 10px rgba(0, 0, 0, 0.4);
}

.ranking-by-stat h2 {
    color: var(--wz-accent-cyan);
    font-size: 1.6em;
    margin-top: 0;
    margin-bottom: 15px;
    text-align: center;
    text-transform: uppercase;
    letter-spacing: 1px;
}

.ranking-table-container {
    overflow-x: auto; /* Pour gérer les tableaux sur les petits écrans */
}

.ranking-table {
    width: 100%;
    border-collapse: collapse;
    color: var(--wz-text-light);
    font-size: 0.9em;
}

.ranking-table thead th {
    background-color: var(--wz-bg-dark);
    color: var(--wz-text-medium);
    padding: 12px 15px;
    text-align: left;
    font-weight: bold;
    text-transform: uppercase;
    letter-spacing: 1px;
}

.ranking-table tbody td {
    padding: 10px 15px;
    border-bottom: 1px solid var(--wz-bg-darker);
}

.ranking-table tbody tr:last-child td {
    border-bottom: none;
}

.ranking-table tbody tr:nth-child(even) {
    background-color: rgba(0, 0, 0, 0.1);
}

.ranking-table th.sortable {
    cursor: pointer;
    user-select: none;
}

.ranking-table th.sortable:hover {
    background-color: var(--wz-accent-yellow);
    color: var(--wz-text-dark);
}

.ranking-table th.active {
    color: var(--wz-accent-cyan);
}

.ranking-table th .sort-icon {
    margin-left: 5px;
    font-size: 0.8em;
}
</style>