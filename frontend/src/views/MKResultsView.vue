<script setup>
import { ref, onMounted, computed } from 'vue'; // watch retiré si non utilisé directement ici
import { useRoute, RouterLink } from 'vue-router';
import apiClient from '@/services/apiClient';
import logoWarzone from '@/assets/images/logo-warzone.png';
import killImage from '@/assets/images/kill-image.png';
import reaImage from '@/assets/images/rea-image.png';
import goulagImage from '@/assets/images/goulag-image.png';
import deployImage from '@/assets/images/deploy-image.png';
import mapWarzoneImage from '@/assets/images/map_warzone_placeholder.jpg'; // ASSUREZ-VOUS D'AVOIR CETTE IMAGE

import { Line } from 'vue-chartjs';
import {
  Chart as ChartJS, Title, Tooltip, Legend, LineElement,
  CategoryScale, LinearScale, PointElement, Filler
} from 'chart.js';

const allLinesDrawn = ref(false);
const chartInstanceRef = ref(null);

const labelOnLineEndPlugin = {
  id: 'labelOnLineEnd',
  afterDatasetsDraw(chart) {
    if (!allLinesDrawn.value) return;
    const { ctx, data, chartArea } = chart;
    if (!chartArea) return;
    ctx.save();
    const yPositionsOccupied = {};
    data.datasets.forEach((dataset, i) => {
      const meta = chart.getDatasetMeta(i);
      if (meta.data.length > 0) {
        const lastPoint = meta.data[meta.data.length - 1];
        const x = lastPoint.x + 10;
        let yPos = Math.round(lastPoint.y);
        const fontSize = 11;
        ctx.font = `bold ${fontSize}px "Roboto Condensed", Arial, sans-serif`;
        ctx.fillStyle = dataset.borderColor || 'white';
        ctx.textAlign = 'left';
        ctx.textBaseline = 'middle';
        let attempt = 0;
        while(yPositionsOccupied[yPos] && Math.abs(yPositionsOccupied[yPos] - x) < 10 && attempt < 10) {
            yPos += (i % 2 === 0 ? fontSize : -fontSize);
            attempt++;
        }
        yPositionsOccupied[yPos] = x;
        if (yPos < chartArea.top + fontSize / 2) yPos = chartArea.top + fontSize / 2;
        if (yPos > chartArea.bottom - fontSize / 2) yPos = chartArea.bottom - fontSize / 2;
        ctx.fillText(dataset.label, x, yPos);
      }
    });
    ctx.restore();
  }
};
ChartJS.register(Title, Tooltip, Legend, LineElement, CategoryScale, LinearScale, PointElement, Filler, labelOnLineEndPlugin);

const route = useRoute();
const mkId = ref(route.params.id);

const masterkillEvent = ref(null);
const aggregatedStats = ref([]);
const finalScores = ref({});
const isLoadingMKDetails = ref(true);
const isLoadingAggregatedStats = ref(true);
const error = ref(null);
const BONUS_POINTS_AWARD = 10;

const reel1Items = ref([
  { id: 'kills', text: 'Kills', icon: killImage, statField: 'total_kills', modifierPref: 'max' },
  { id: 'revives', text: 'Réanimations', icon: reaImage, statField: 'total_revives_done', modifierPref: 'max' },
  { id: 'gulags', text: 'Goulags Gagnés', icon: goulagImage, statField: 'total_gulag_wins', modifierPref: 'max' },
  { id: 'deaths', text: 'Moins de Morts', icon: '⚰️', statField: 'total_deaths', modifierPref: 'min' },
  { id: 'rage_quits', text: 'Fair-play', icon: '🧘', statField: 'total_rage_quits', modifierPref: 'min'},
  { id: 'redeployed', text: 'Autonomie', icon: deployImage, statField: 'total_times_redeployed_by_teammate', modifierPref: 'min' },
]);
const reel2Items = ref([
  { id: 'plus', text: '+', modifier: 'max', description: 'Le Plus Élevé' },
  { id: 'minus', text: '-', modifier: 'min', description: 'Le Plus Bas / Le Moins' }
]);

const reel1Display = ref({ icon: logoWarzone, text: '?' });
const reel2Display = ref({ text: '?' });
const reel3Display = ref({ text: '?' });
const finalReel1Value = ref(null);
const finalReel2Value = ref(null);
const finalReel3Value = ref(null);
const isSpinning = ref(false);
const bonusAwardLogEntry = ref(null);
const bonusAwarded = ref(false);

const gameByGameScoresData = ref(null);
const isLoadingGraphData = ref(false);
const chartLabels = ref([]);
const chartDatasets = ref([]);

const mapLocations = ref({
  'Airport': { name: 'Airport', x: 15, y: 25 },
  'Stadium': { name: 'Stadium', x: 50, y: 30 },
  'Downtown': { name: 'Downtown', x: 45, y: 60 },
  'Superstore': { name: 'Superstore', x: 35, y: 50 },
});
const selectedMapLocation = ref(null);

const chartData = computed(() => ({ labels: chartLabels.value, datasets: chartDatasets.value }));
const chartOptions = ref({
  responsive: true, maintainAspectRatio: false, tension: 0.4,
  animation: { duration: 1000, easing: 'easeInOutQuad' },
  scales: {
    y: { beginAtZero: true, ticks: { color: 'var(--wz-text-medium)', padding: 5 }, grid: { color: 'var(--wz-border-color)' } },
    x: { ticks: { color: 'var(--wz-text-medium)', padding: 5 }, grid: { color: 'var(--wz-border-color)' } }
  },
  plugins: {
    legend: { display: false },
    tooltip: { titleFont: { weight: 'bold'}, bodyFont: {size: 14} },
    labelOnLineEnd: {}
  }
});

let reelIntervals = [];
function startAllReelSpinEffects() {
  isSpinning.value = true;
  finalReel1Value.value = null; finalReel2Value.value = null; finalReel3Value.value = null;
  bonusAwardLogEntry.value = null;
  reelIntervals.forEach(clearInterval); reelIntervals = [];
  const spin = (reelDisplayRef, items, displayExtractor) => setInterval(() => { reelDisplayRef.value = displayExtractor(items[Math.floor(Math.random() * items.length)]); }, 120);
  reelIntervals.push(spin(reel1Display, reel1Items.value, item => ({ icon: item.icon, text: item.text }) ));
  reelIntervals.push(spin(reel2Display, reel2Items.value, item => ({ text: item.text }) ));
  const playersForReel = aggregatedStats.value.map(s => s.player).filter(p => p); // S'assurer que les joueurs existent
  if (playersForReel.length > 0) {
    reelIntervals.push(spin(reel3Display, playersForReel, item => ({ text: item?.gamertag || "???" }) ));
  } else {
     reel3Display.value = { text: "N/A" }; // Cas où il n'y a pas de joueurs
  }
}
function stopReelEffect(intervalIndex, finalValue, reelDisplayRef, displayExtractor) {
  if (reelIntervals[intervalIndex]) clearInterval(reelIntervals[intervalIndex]);
  reelDisplayRef.value = displayExtractor(finalValue);
}

async function awardSingleBonus() {
  if (!masterkillEvent.value || !masterkillEvent.value.has_bonus_reel || bonusAwarded.value || !aggregatedStats.value || aggregatedStats.value.length === 0) {
    allBonusesProcessedActions(); return;
  }
  startAllReelSpinEffects();
  const reel1StopTime = Math.random() * 2000 + 3000; // Réduit un peu pour aller plus vite
  const reel2StopTime = reel1StopTime + Math.random() * 1500 + 2000;
  const reel3StopTime = reel2StopTime + Math.random() * 1500 + 2000;

  setTimeout(() => {
    const randomIndex1 = Math.floor(Math.random() * reel1Items.value.length);
    finalReel1Value.value = reel1Items.value[randomIndex1];
    stopReelEffect(0, finalReel1Value.value, reel1Display, item => ({ icon: item.icon, text: item.text }));
  }, reel1StopTime);

  setTimeout(() => {
    if (!finalReel1Value.value) { allBonusesProcessedActions(); return; }
    let chosenReel2Item;
    if (finalReel1Value.value.modifierPref && Math.random() > 0.2) chosenReel2Item = reel2Items.value.find(item => item.modifier === finalReel1Value.value.modifierPref);
    else chosenReel2Item = reel2Items.value[Math.floor(Math.random() * reel2Items.value.length)];
    if (finalReel1Value.value.id && ['deaths', 'rage_quits', 'redeployed'].includes(finalReel1Value.value.id)) chosenReel2Item = reel2Items.value.find(item => item.modifier === 'min');
    finalReel2Value.value = chosenReel2Item;
    stopReelEffect(1, finalReel2Value.value, reel2Display, item => ({ text: item.text }));
  }, reel2StopTime);

  setTimeout(async () => {
    stopReelEffect(2, {text: '...'}, reel3Display, item => item);
    isSpinning.value = false;
    if (!finalReel1Value.value || !finalReel2Value.value) { finalReel3Value.value = { gamertag: "Erreur" }; allBonusesProcessedActions(); return; }
    let targetValue = (finalReel2Value.value.modifier === 'max') ? -Infinity : Infinity;
    let eligiblePlayers = []; const statField = finalReel1Value.value.statField;
    aggregatedStats.value.forEach(pStat => {
        const statVal = pStat[statField];
        const statValue = (statVal === undefined || statVal === null) ? (finalReel2Value.value.modifier === 'max' ? -Infinity : Infinity) : Number(statVal);
        if (finalReel2Value.value.modifier === 'max') {
            if (statValue > targetValue) { targetValue = statValue; eligiblePlayers = [pStat.player]; }
            else if (statValue === targetValue && targetValue > -Infinity && targetValue !== 0) { eligiblePlayers.push(pStat.player); } // Ne pas ajouter pour 0 sauf si c'est le seul
        } else { // min
            if (statValue < targetValue) { targetValue = statValue; eligiblePlayers = [pStat.player]; }
            else if (statValue === targetValue) { eligiblePlayers.push(pStat.player); }
        }
    });

    if (eligiblePlayers.length > 0 && (finalReel2Value.value.modifier === 'min' || targetValue > 0 || (targetValue === 0 && statField !== 'total_deaths'))) { // Permettre 0 si ce n'est pas pour les morts
      finalReel3Value.value = eligiblePlayers[Math.floor(Math.random() * eligiblePlayers.length)];
      reel3Display.value = { text: finalReel3Value.value.gamertag };
      const currentScore = finalScores.value[finalReel3Value.value.id.toString()] || 0;
      finalScores.value[finalReel3Value.value.id.toString()] = currentScore + BONUS_POINTS_AWARD;
      bonusAwardLogEntry.value = { criterion: finalReel1Value.value, modifier: finalReel2Value.value, player: finalReel3Value.value, points: BONUS_POINTS_AWARD, valueAchieved: targetValue };
      try {
        await apiClient.post(`/masterkillevents/${mkId.value}/apply_bonus/`, {
            player_id: finalReel3Value.value.id,
            bonus_points: BONUS_POINTS_AWARD,
            reason: `${finalReel1Value.value.text} (${finalReel2Value.value.description || finalReel2Value.value.text})`
        });
      } catch (apiError) {
          console.error("Erreur enregistrement bonus serveur:", apiError);
          finalScores.value[finalReel3Value.value.id.toString()] = currentScore;
          bonusAwardLogEntry.value.points = 0;
          bonusAwardLogEntry.value.player.gamertag += " (Erreur Bonus)";
      }
    } else {
      finalReel3Value.value = { gamertag: "Personne !" }; reel3Display.value = { text: "Personne !" };
      bonusAwardLogEntry.value = { criterion: finalReel1Value.value, modifier: finalReel2Value.value, player: {gamertag: "Personne !"}, points: 0, valueAchieved: targetValue };
    }
    allBonusesProcessedActions();
  }, reel3StopTime);
}

function allBonusesProcessedActions() {
  bonusAwarded.value = true; isSpinning.value = false;
  reelIntervals.forEach(clearInterval); reelIntervals = [];
  fetchGameByGameScoresForChart();
}

async function fetchDataAndInitBonuses() {
  isLoadingMKDetails.value = true; isLoadingAggregatedStats.value = true;
  error.value = null; bonusAwarded.value = false; bonusAwardLogEntry.value = null; allLinesDrawn.value = false;
  try {
    const mkPromise = apiClient.get(`/masterkillevents/${mkId.value}/`);
    const statsPromise = apiClient.get(`/masterkillevents/${mkId.value}/aggregated-stats/`);
    const [mkResponse, statsResponse] = await Promise.all([mkPromise, statsPromise]);

    masterkillEvent.value = mkResponse.data; isLoadingMKDetails.value = false;
    aggregatedStats.value = statsResponse.data; isLoadingAggregatedStats.value = false;

    if (masterkillEvent.value && aggregatedStats.value) {
      aggregatedStats.value.forEach(pStat => {
        finalScores.value[pStat.player.id.toString()] = pStat.total_score_from_games || 0;
      });
    } else {
        error.value = "Données MK ou Stats Agrégées manquantes.";
        allLinesDrawn.value = true; return;
    }
    
    if (masterkillEvent.value?.status === 'completed' && masterkillEvent.value.has_bonus_reel && !bonusAwarded.value) { 
      awardSingleBonus(); 
    } else if (masterkillEvent.value?.status === 'completed') { 
      allBonusesProcessedActions(); 
    } else { 
      allLinesDrawn.value = true; 
      error.value = "Cet événement Masterkill n'est pas encore terminé pour afficher les résultats.";
    }
  } catch (err) { 
    error.value = "Impossible de charger les données initiales du Masterkill pour les résultats."; 
    isLoadingMKDetails.value = false; isLoadingAggregatedStats.value = false;
    allLinesDrawn.value = true;
  }
}

async function fetchGameByGameScoresForChart() {
  if (!masterkillEvent.value) { allLinesDrawn.value = true; return; }
  if (masterkillEvent.value.status !== 'completed') {
    allLinesDrawn.value = true; return;
  }
  isLoadingGraphData.value = true; allLinesDrawn.value = false;
  try {
    const response = await apiClient.get(`/masterkillevents/${mkId.value}/game-scores/`);
    gameByGameScoresData.value = response.data;
    if (gameByGameScoresData.value?.player_scores_per_game) {
        prepareChartDataForAnimation();
    } else { chartLabels.value = []; chartDatasets.value = []; allLinesDrawn.value = true; }
  } catch (err) { console.error("Erreur fetch scores par partie:", err); allLinesDrawn.value = true; }
  finally { isLoadingGraphData.value = false; }
}

function prepareChartDataForAnimation() {
  if (!gameByGameScoresData.value || !masterkillEvent.value?.participants_details) {
    chartLabels.value = []; chartDatasets.value = []; allLinesDrawn.value = true; return;
  }
  const numGamesForChart = gameByGameScoresData.value.num_games_played ?? masterkillEvent.value.num_games_planned ?? 0;
  const participantDetailsForChart = gameByGameScoresData.value.participants || masterkillEvent.value.participants_details;
  const scoresPerGameFromAPI = gameByGameScoresData.value.player_scores_per_game;

  if (!participantDetailsForChart || participantDetailsForChart.length === 0) { allLinesDrawn.value = true; return; }
  
  if (numGamesForChart === 0 && Object.keys(finalScores.value).length > 0) {
    chartLabels.value = ["Début", "Score Final"];
    chartDatasets.value = participantDetailsForChart.map(player => {
        const r = Math.floor(Math.random() * 180) + 75; const g = Math.floor(Math.random() * 180) + 75; const b = Math.floor(Math.random() * 180) + 75;
        const finalScoreWithBonus = finalScores.value[player.id.toString()] || 0;
        return {
            label: player.gamertag, data: [0, finalScoreWithBonus], borderColor: `rgb(${r},${g},${b})`,
            backgroundColor: `rgba(${r},${g},${b},0.15)`, tension: 0.4, fill: 'origin',
            pointRadius: 5, pointBackgroundColor: `rgb(${r},${g},${b})`,
            pointHoverRadius: 7, pointHoverBorderWidth: 2, borderWidth: 3,
        };
    });
    allLinesDrawn.value = true; return;
  }

  chartDatasets.value = participantDetailsForChart.map(player => {
    const r = Math.floor(Math.random() * 180) + 75; const g = Math.floor(Math.random() * 180) + 75; const b = Math.floor(Math.random() * 180) + 75;
    return {
      label: player.gamertag, data: [0], borderColor: `rgb(${r},${g},${b})`,
      backgroundColor: `rgba(${r},${g},${b},0.15)`, tension: 0.4, fill: 'origin',
      pointRadius: 5, pointBackgroundColor: `rgb(${r},${g},${b})`,
      pointHoverRadius: 7, pointHoverBorderWidth: 2, borderWidth: 3,
    };
  });
  chartLabels.value = ["Début"];

  let gameIndexToDisplay = 0;
  function addNextDataPoint() {
    if (gameIndexToDisplay < numGamesForChart) {
      chartLabels.value = [...chartLabels.value, `Partie ${gameIndexToDisplay + 1}`];
      chartDatasets.value = chartDatasets.value.map((dataset) => {
        const originalPlayer = participantDetailsForChart.find(p => p.gamertag === dataset.label);
        let currentDataArray = [...dataset.data];
        let nextScore = currentDataArray[currentDataArray.length - 1];
        if (originalPlayer && scoresPerGameFromAPI[originalPlayer.id.toString()] && scoresPerGameFromAPI[originalPlayer.id.toString()].length > gameIndexToDisplay) {
          nextScore = scoresPerGameFromAPI[originalPlayer.id.toString()][gameIndexToDisplay];
        }
        currentDataArray.push(nextScore);
        return { ...dataset, data: currentDataArray };
      });
      gameIndexToDisplay++;
      if (gameIndexToDisplay < numGamesForChart) {
        setTimeout(addNextDataPoint, 1600);
      } else {
        addFinalBonusPointToChart();
      }
    } else {
        addFinalBonusPointToChart();
    }
  }
  if (numGamesForChart > 0) setTimeout(addNextDataPoint, 700);
  else addFinalBonusPointToChart();
}

function addFinalBonusPointToChart() {
  const finalLabel = "Score Final";
  if (chartLabels.value.length > 0 && chartLabels.value[chartLabels.value.length -1] !== finalLabel) {
      chartLabels.value = [...chartLabels.value, finalLabel];
  } else if (chartLabels.value.length === 0) {
      chartLabels.value = ["Début", finalLabel];
  }

  chartDatasets.value = chartDatasets.value.map(dataset => {
    const originalPlayer = (gameByGameScoresData.value?.participants || masterkillEvent.value?.participants_details || []).find(p => p.gamertag === dataset.label);
    let finalScoreVal = dataset.data.length > 0 ? dataset.data[dataset.data.length - 1] : 0;
    if (originalPlayer && finalScores.value[originalPlayer.id.toString()] !== undefined) {
      finalScoreVal = finalScores.value[originalPlayer.id.toString()];
    }
    let newDataArray = [...dataset.data];
    if (chartLabels.value[chartLabels.value.length - 1] === finalLabel) {
        if (newDataArray.length === chartLabels.value.length -1) {
            newDataArray.push(finalScoreVal);
        } else if (newDataArray.length === chartLabels.value.length) {
            newDataArray[newDataArray.length - 1] = finalScoreVal;
        }
    }
    return { ...dataset, data: newDataArray };
  });

  setTimeout(() => {
    allLinesDrawn.value = true;
    if (chartInstanceRef.value?.chart) {
        chartInstanceRef.value.chart.update('none');
    }
  }, chartOptions.value.animation.duration + 100);
}

const rankedPlayers = computed(() => {
  if (!aggregatedStats.value || aggregatedStats.value.length === 0 || Object.keys(finalScores.value).length === 0) {
    if (aggregatedStats.value.length > 0) {
        return [...aggregatedStats.value]
            .map(pStat => ({
                playerId: pStat.player.id.toString(),
                gamertag: pStat.player.gamertag,
                gameScore: pStat.total_score_from_games || 0,
                bonusAwarded: 0,
                totalScore: pStat.total_score_from_games || 0,
                finalScore: pStat.total_score_from_games || 0,
            }))
            .sort((a, b) => b.totalScore - a.totalScore)
            .map((p, index) => ({ ...p, rank: index + 1 }));
    }
    return [];
  }
  return Object.entries(finalScores.value).map(([playerId, score]) => {
    const playerAggStats = aggregatedStats.value.find(p => p.player.id.toString() === playerId);
    const playerInfo = playerAggStats?.player;
    const initialScore = playerAggStats?.total_score_from_games || 0;
    return {
      playerId: playerId,
      gamertag: playerInfo?.gamertag || 'N/A',
      gameScore: initialScore,
      totalScore: score,
      bonusAwarded: score - initialScore,
      finalScore: score,
    };
  }).sort((a, b) => b.totalScore - a.totalScore)
    .map((p, index) => ({ ...p, rank: index + 1 }));
});

const completedGamesCountInMKFromResults = computed(() => {
    if (gameByGameScoresData.value && gameByGameScoresData.value.num_games_played !== undefined) {
        return gameByGameScoresData.value.num_games_played;
    }
    return masterkillEvent.value?.games?.filter(g => g.status === 'completed').length || 0;
});

function calculateKDRatio(kills, deaths) {
  const k = Number(kills) || 0;
  const d = Number(deaths) || 0;
  if (d === 0) return k > 0 ? '∞' : (0).toFixed(2);
  return (k / d).toFixed(2);
}

const durationOfMKResults = computed(() => {
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

const averageKillsPerGameOverallResults = computed(() => {
    if (masterkillEvent.value && aggregatedStats.value.length > 0 && completedGamesCountInMKFromResults.value > 0) {
        const totalKillsAllPlayers = aggregatedStats.value.reduce((sum, pStat) => sum + (pStat.total_kills || 0), 0);
        return (totalKillsAllPlayers / completedGamesCountInMKFromResults.value).toFixed(1);
    }
    return 'N/A';
});

const detailedPlayerStatsResults = computed(() => {
  if (!aggregatedStats.value || aggregatedStats.value.length === 0 || !masterkillEvent.value) return [];
  return aggregatedStats.value.map(pStat => {
    const kills = pStat.total_kills || 0;
    const deaths = pStat.total_deaths || 0;
    const gamesPlayed = pStat.games_played_in_mk ?? completedGamesCountInMKFromResults.value ?? 0;
    const gulagWins = pStat.total_gulag_wins || 0;
    const gulagLost = pStat.total_gulag_lost || 0;
    const scoreWithBonus = finalScores.value[pStat.player.id.toString()] ?? (pStat.total_score_from_games || 0);

    return {
      id: pStat.player.id,
      gamertag: pStat.player.gamertag,
      total_kills: kills,
      total_deaths: deaths,
      kd_ratio: calculateKDRatio(kills, deaths),
      total_assists: pStat.total_assists || 0,
      total_revives_done: pStat.total_revives_done || 0,
      average_kills_per_game: gamesPlayed > 0 ? (kills / gamesPlayed).toFixed(1) : '0.0',
      total_gulag_wins: gulagWins,
      total_gulag_lost: gulagLost, 
      gulag_win_ratio: (gulagWins + gulagLost > 0) ? ((gulagWins / (gulagWins + gulagLost)) * 100).toFixed(1) + '%' : 'N/A',
      total_score_from_games: scoreWithBonus
    };
  }).sort((a,b) => b.total_score_from_games - a.total_score_from_games);
});

onMounted(() => {
  fetchDataAndInitBonuses();
});
</script>

<template>
  <div class="mk-results-view">
    <header class="page-header">
      <img :src="logoWarzone" alt="Warzone Logo" class="warzone-logo" />
      <h1 v-if="masterkillEvent">RÉSULTATS MASTERKILL: {{ masterkillEvent.name }}</h1>
      <h1 v-else-if="isLoadingMKDetails || isLoadingAggregatedStats">Calcul des Résultats...</h1>
      <h1 v-else>Résultats Masterkill</h1>
    </header>

    <div class="content-wrapper-results">
      <div v-if="isLoadingMKDetails || (isLoadingAggregatedStats && masterkillEvent && masterkillEvent.has_bonus_reel && !bonusAwarded)" class="loading">
        Analyse des performances et calcul du bonus...
      </div>
      <div v-else-if="error" class="error-message">{{ error }}</div>
      <div v-else-if="masterkillEvent">

        <div v-if="masterkillEvent.has_bonus_reel && !bonusAwarded && masterkillEvent.status === 'completed'" class="bonus-slot-machine">
          <h2><span class="icon-star">⭐</span> ROULEAU BONUS <span class="icon-star">⭐</span></h2>
          <div class="reels-container">
            <div class="reel" :class="{'is-spinning': isSpinning}">
              <div class="reel-value criterion">
                <img
                  v-if="typeof reel1Display.icon === 'string' && reel1Display.icon.includes('/')"
                  :src="reel1Display.icon"
                  alt="Critère"
                  class="reel-img-icon"
                />
                <span v-else class="reel-emoji-icon">{{ reel1Display.icon }}</span>
                <span>{{ reel1Display.text }}</span>
              </div>
            </div>
            <div class="reel" :class="{'is-spinning': isSpinning}">
              <div class="reel-value modifier"><span>{{ reel2Display.text }}</span></div>
            </div>
            <div class="reel" :class="{'is-spinning': isSpinning}">
              <div class="reel-value player"><span>{{ reel3Display.text }}</span></div>
            </div>
          </div>
          <p v-if="isSpinning">Attribution du bonus...</p>
        </div>

        <div class="bonus-log-section" v-if="bonusAwardLogEntry && bonusAwarded && masterkillEvent.has_bonus_reel">
          <h3><span class="icon-target">🎯</span> Bonus Spécial Attribué :</h3>
          <div class="bonus-log-item unique-bonus">
            <img
              v-if="bonusAwardLogEntry.criterion?.icon && typeof bonusAwardLogEntry.criterion.icon === 'string' && bonusAwardLogEntry.criterion.icon.includes('/')"
              :src="bonusAwardLogEntry.criterion.icon"
              alt="Icon"
              class="log-img-icon"
            />
            <span v-else-if="bonusAwardLogEntry.criterion?.icon" class="log-emoji-icon">
              {{ bonusAwardLogEntry.criterion.icon }}
            </span>
            <span class="bonus-text">
              {{ bonusAwardLogEntry.criterion?.text }}
              <span class="bonus-mod">({{ bonusAwardLogEntry.modifier?.description || bonusAwardLogEntry.modifier?.text }})</span>
              pour {{ bonusAwardLogEntry.valueAchieved }}
            </span>
            <span class="player-name">{{ bonusAwardLogEntry.player?.gamertag }}</span>
            <span class="points-awarded" v-if="bonusAwardLogEntry.points > 0">+{{ bonusAwardLogEntry.points }} pts!</span>
            <span v-else>Pas de points.</span>
          </div>
        </div>
        
        <div v-if="bonusAwarded || (masterkillEvent.status === 'completed' && !masterkillEvent.has_bonus_reel)">
          <hr v-if="bonusAwardLogEntry || !masterkillEvent.has_bonus_reel" />

          <div class="details-grid summary-info-results">
              <p><strong>Durée du MK:</strong> {{ durationOfMKResults }}</p>
              <p v-if="completedGamesCountInMKFromResults > 0"><strong>Moy. Kills/Partie (Global):</strong> {{ averageKillsPerGameOverallResults }}</p>
              <p><strong>Gage:</strong> {{ masterkillEvent.selected_gage_text || 'Aucun' }}</p>
          </div>
          <hr>

          <div class="mario-party-graph-section" v-if="gameByGameScoresData">
            <h2>📈 Évolution des Scores 📈</h2>
            <div class="chart-container">
              <Line
                v-if="chartData.datasets.length && allLinesDrawn"
                :data="chartData"
                :options="chartOptions"
                :key="`result-chart-${mkId}`"
                ref="chartInstanceRef"
              />
              <p v-else-if="masterkillEvent.status === 'completed'" class="loading">Animation du graphique...</p>
            </div>
          </div>
          <hr v-if="gameByGameScoresData">

          <h2 v-if="allLinesDrawn">🏆 Classement Final 🏆</h2>
          <table v-if="allLinesDrawn && rankedPlayers.length" class="results-table">
            <thead>
              <tr>
                <th>Rang</th>
                <th>Opérateur</th>
                <th>Score Parties</th>
                <th>Bonus</th>
                <th>Score Final</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="(player, index) in rankedPlayers"
                :key="player.playerId"
                :class="{'winner-row': index === 0}">
                <td>#{{ player.rank }}</td>
                <td>{{ player.gamertag }}</td>
                <td>{{ player.gameScore }}</td>
                <td>
                  {{
                    player.bonusAwarded > 0
                      ? `+${player.bonusAwarded}`
                      : player.bonusAwarded < 0
                      ? player.bonusAwarded
                      : '0'
                  }}
                </td>
                <td><strong>{{ player.finalScore }}</strong></td>
              </tr>
            </tbody>
          </table>
          <p v-if="allLinesDrawn && rankedPlayers.length > 0 && masterkillEvent.status === 'completed'" class="overall-winner-announce">
            Vainqueur : <strong>{{ rankedPlayers[0].gamertag }}</strong> !
          </p>
          <hr v-if="allLinesDrawn && rankedPlayers.length">

          <div v-if="allLinesDrawn" class="detailed-stats-section-results">
            <h3>Statistiques Détaillées Finales</h3>
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
                    <tr v-for="playerStat in detailedPlayerStatsResults" :key="`results-stat-${playerStat.id}`">
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
          <hr v-if="allLinesDrawn">
          
          <div v-if="allLinesDrawn" class="map-section-container-results">
              <h3>Carte des Spawns</h3>
              <div class="location-selector-mk-results">
                  <label for="location-select-results">Lieu d'intérêt :</label>
                  <select id="location-select-results" v-model="selectedMapLocation">
                  <option :value="null">-- Aucun Lieu --</option>
                  <option v-for="(details, name) in mapLocations" :key="name" :value="name">
                      {{ details.name }}
                  </option>
                  </select>
              </div>
              <div class="map-container-mk-results">
                  <img :src="mapWarzoneImage" alt="Carte Warzone" class="map-background-image-results">
                   <div
                    v-if="selectedMapLocation && mapLocations[selectedMapLocation]"
                    class="map-point-results selected-spawn-point"
                    :style="{ 
                      left: mapLocations[selectedMapLocation].x + '%', 
                      top: mapLocations[selectedMapLocation].y + '%' 
                    }"
                    :title="mapLocations[selectedMapLocation].name"
                  >★</div>
                  <div v-for="(game, index) in masterkillEvent.games.filter(g => g.status === 'completed' && g.spawn_location && mapLocations[g.spawn_location])" 
                      :key="`spawn-point-res-${game.id || index}`"
                      class="map-point-results game-spawn-point"
                      :style="{ left: mapLocations[game.spawn_location].x + '%', top: mapLocations[game.spawn_location].y + '%' }"
                      :title="`${mapLocations[game.spawn_location].name} (Partie ${game.game_number})`"
                  >{{ game.game_number }}</div>
              </div>
          </div>
        </div>

        <div class="navigation-actions">
          <RouterLink :to="{ name: 'home' }" class="action-btn">Retour Liste MK</RouterLink>
          <RouterLink :to="{ name: 'masterkill-detail', params: { id: mkId } }" class="action-btn">Revoir Détails du MK</RouterLink>
        </div>
      </div>
      <p v-else>Données de résultats non disponibles.</p>
    </div>
  </div>
</template>

<style scoped>
.mk-results-view { min-height: 100vh; font-family: "Agency FB", "Roboto Condensed", Arial, sans-serif; background-color: var(--wz-bg-dark); background-image: linear-gradient(rgba(16, 16, 16, 0.92), rgba(16, 16, 16, 0.98)), url('@/assets/images/map-background.jpg'); background-size: cover; background-position: center center; background-attachment: fixed; color: var(--wz-text-light); padding-bottom: 40px; }
.page-header { background-color: rgba(0,0,0,0.6); padding: 20px; text-align: center; border-bottom: 3px solid var(--wz-accent-yellow); margin-bottom: 30px; }
.warzone-logo { max-height: 70px; margin-bottom: 15px; }
.page-header h1 { color: var(--wz-text-light); font-size: 2.2em; text-transform: uppercase; letter-spacing: 3px; margin: 0; border-bottom: none; font-weight: 700; }
.content-wrapper-results { width: 80vw; margin-left: auto; margin-right: auto; background-color: rgba(30, 30, 30, 0.92); padding: 30px; border-radius: 8px; box-shadow: 0 5px 25px rgba(0,0,0,0.7); }
.loading, .error-message { text-align: center; padding: 30px; color: var(--wz-text-medium); font-size: 1.2em;}
.error-message { color: var(--wz-text-dark); background-color: var(--wz-accent-red); border: 1px solid #c00;}
.bonus-slot-machine h2, .mk-results-view h2 { color: var(--wz-accent-cyan); text-align: center; font-size: 1.8em; margin-bottom: 20px; text-transform: uppercase; border-bottom: 1px solid var(--wz-border-color); padding-bottom: 10px; }
.icon-star { color: var(--wz-accent-yellow); }
.bonus-slot-machine { text-align: center; margin-bottom: 30px; padding: 20px; background-color: var(--wz-bg-medium); border-radius: 8px; border: 2px solid var(--wz-accent-yellow); }
.bonus-slot-machine p { color: var(--wz-text-medium); margin-bottom: 20px; }
.reels-container { display: flex; justify-content: space-around; gap: 10px; margin-bottom: 20px; padding: 10px; background-color: rgba(0,0,0,0.3); border-radius: 6px; }
.reel { flex: 1; min-width: 150px; max-width: 220px; height: 100px; background-color: var(--wz-bg-dark); border: 3px solid var(--wz-border-color); border-image: linear-gradient(to bottom, var(--wz-accent-yellow), var(--wz-border-color)) 1; border-radius: 6px; display: flex; align-items: center; justify-content: center; overflow: hidden; box-shadow: inset 0 0 15px rgba(0,0,0,0.7); text-align: center; font-size: 1.1em; }
.reel-value { padding: 5px; display: flex; flex-direction: column; align-items: center; justify-content: center; }
.reel-value.criterion .reel-img-icon { width: 40px; height: 40px; object-fit: contain; margin-bottom: 3px; }
.reel-value.criterion .reel-emoji-icon { font-size: 1.8em; display:block; margin-bottom: 3px;}
.reel-value.criterion span:last-child {font-size: 0.75em; text-transform: uppercase; letter-spacing: 1px; margin-top: 2px;}
.reel-value.modifier span { font-size: 2.5em; font-weight: bold; color: var(--wz-accent-yellow); }
.reel-value.player span { font-size: 1.1em; font-weight: bold; color: var(--wz-accent-green); }
.reel.is-spinning .reel-value { animation: veryFastBlinker 0.15s linear infinite; } /* Un peu moins vite */
@keyframes veryFastBlinker { 50% { opacity: 0.5; } }
.bonus-log-section { margin-top: 20px; margin-bottom:30px; }
.bonus-log-section h3 { color: var(--wz-accent-yellow); text-align: center; margin-bottom: 15px; font-size: 1.5em; border-bottom: none; text-transform: uppercase;}
.bonus-log-item.unique-bonus { background-color: var(--wz-bg-medium); border-left: 5px solid var(--wz-accent-green); font-size: 1.1em; padding: 15px; }
.log-img-icon { width: 24px; height: 24px; object-fit: contain; vertical-align: middle; margin-right: 5px;}
.log-emoji-icon { font-size: 1.2em; vertical-align: middle; margin-right: 5px;}
.bonus-log-item { display: flex; align-items: center; gap: 10px; font-size: 0.95em; background-color: var(--wz-bg-light); padding: 10px 15px; margin-bottom: 8px; border-radius: 4px; border-left: 4px solid var(--wz-accent-cyan); }
.bonus-mod { color: var(--wz-text-medium); margin: 0 5px; }
.player-name { font-weight: bold; color: var(--wz-accent-yellow); }
.points-awarded { font-weight: bold; color: var(--wz-accent-green); margin-left: auto; }
.results-table { width: 100%; border-collapse: collapse; margin-top: 20px; box-shadow: 0 0 15px rgba(0,0,0,0.3); }
.results-table th, .results-table td { padding: 12px 15px; text-align: left; border-bottom: 1px solid var(--wz-border-color); }
.results-table thead th { background-color: var(--wz-bg-light); color: var(--wz-accent-cyan); text-transform: uppercase; font-size: 0.9em; letter-spacing: 1px; }
.results-table td { color: var(--wz-text-medium); }
.results-table td:first-child { font-weight: bold; color: var(--wz-text-light); } /* Rang */
.results-table td:nth-child(2) { font-weight: bold; color: var(--wz-accent-yellow); } /* Opérateur */
.results-table td strong { font-size: 1.1em; color: var(--wz-text-light); } /* Score Final */
.results-table tbody tr:hover { background-color: rgba(255, 255, 255, 0.05); }
.winner-row td { background-color: rgba(76, 175, 80, 0.25) !important; color: #fff !important; font-weight: bold; }
.winner-row td:nth-child(2) { color: var(--wz-accent-green) !important; }
.overall-winner-announce { text-align: center; font-size: 1.5em; color: var(--wz-accent-green); margin-top: 30px; padding: 15px; background-color: var(--wz-bg-medium); border-radius: 5px; }
.overall-winner-announce strong { color: var(--wz-accent-yellow); text-transform: uppercase; }
.mario-party-graph-section { margin-top: 30px; }
.mario-party-graph-section h2 { color: var(--wz-accent-yellow); }
.chart-container { min-height: 350px; padding: 10px; background-color: rgba(0,0,0,0.2); border-radius: 6px; border: 1px solid var(--wz-border-color); }
.navigation-actions { margin-top: 30px; text-align: center; }
.action-btn { display: inline-flex; align-items: center; justify-content: center; gap: 10px; color: var(--wz-text-dark); padding: 12px 22px; border: none; border-radius: 5px; cursor: pointer; margin: 0 10px; font-size: 1em; text-transform: uppercase; font-weight: bold; letter-spacing: 1.2px; transition: all 0.2s ease-in-out; text-decoration: none; background-color: var(--wz-accent-cyan); }
.action-btn:hover { background-color: #29deef; transform: translateY(-2px); }
hr { border: 0; height: 1px; background: var(--wz-border-color); margin: 30px 0; }

.mk-results-view { min-height: 100vh; font-family: "Agency FB", "Roboto Condensed", Arial, sans-serif; background-color: var(--wz-bg-dark); background-image: linear-gradient(rgba(16, 16, 16, 0.92), rgba(16, 16, 16, 0.98)), url('@/assets/images/map-background.jpg'); background-size: cover; background-position: center center; background-attachment: fixed; color: var(--wz-text-light); padding-bottom: 40px; }
.page-header { background-color: rgba(0,0,0,0.6); padding: 20px; text-align: center; border-bottom: 3px solid var(--wz-accent-yellow); margin-bottom: 30px; }
.warzone-logo { max-height: 70px; margin-bottom: 15px; }
.page-header h1 { color: var(--wz-text-light); font-size: 2.2em; text-transform: uppercase; letter-spacing: 3px; margin: 0; border-bottom: none; font-weight: 700; }
.content-wrapper-results { width: 90vw; max-width: 1400px; margin-left: auto; margin-right: auto; background-color: rgba(30, 30, 30, 0.92); padding: 30px; border-radius: 8px; box-shadow: 0 5px 25px rgba(0,0,0,0.7); }
.loading, .error-message { text-align: center; padding: 30px; color: var(--wz-text-medium); font-size: 1.2em;}
.error-message { color: var(--wz-text-dark); background-color: var(--wz-accent-red); border: 1px solid #c00;}
.bonus-slot-machine h2, .mk-results-view h2 { color: var(--wz-accent-cyan); text-align: center; font-size: 1.8em; margin-bottom: 20px; text-transform: uppercase; border-bottom: 1px solid var(--wz-border-color); padding-bottom: 10px; }
.icon-star { color: var(--wz-accent-yellow); }
.bonus-slot-machine { text-align: center; margin-bottom: 30px; padding: 20px; background-color: var(--wz-bg-medium); border-radius: 8px; border: 2px solid var(--wz-accent-yellow); }
.bonus-slot-machine p { color: var(--wz-text-medium); margin-bottom: 20px; }
.reels-container { display: flex; justify-content: space-around; gap: 10px; margin-bottom: 20px; padding: 10px; background-color: rgba(0,0,0,0.3); border-radius: 6px; }
.reel { flex: 1; min-width: 150px; max-width: 220px; height: 100px; background-color: var(--wz-bg-dark); border: 3px solid var(--wz-border-color); border-image: linear-gradient(to bottom, var(--wz-accent-yellow), var(--wz-border-color)) 1; border-radius: 6px; display: flex; align-items: center; justify-content: center; overflow: hidden; box-shadow: inset 0 0 15px rgba(0,0,0,0.7); text-align: center; font-size: 1.1em; }
.reel-value { padding: 5px; display: flex; flex-direction: column; align-items: center; justify-content: center; }
.reel-value.criterion .reel-img-icon { width: 40px; height: 40px; object-fit: contain; margin-bottom: 3px; }
.reel-value.criterion .reel-emoji-icon { font-size: 1.8em; display:block; margin-bottom: 3px;}
.reel-value.criterion span:last-child {font-size: 0.75em; text-transform: uppercase; letter-spacing: 1px; margin-top: 2px;}
.reel-value.modifier span { font-size: 2.5em; font-weight: bold; color: var(--wz-accent-yellow); }
.reel-value.player span { font-size: 1.1em; font-weight: bold; color: var(--wz-accent-green); }
.reel.is-spinning .reel-value { animation: veryFastBlinker 0.15s linear infinite; }
@keyframes veryFastBlinker { 50% { opacity: 0.5; } }
.bonus-log-section { margin-top: 20px; margin-bottom:30px; }
.bonus-log-section h3 { color: var(--wz-accent-yellow); text-align: center; margin-bottom: 15px; font-size: 1.5em; border-bottom: none; text-transform: uppercase;}
.icon-target {margin-right: 8px;}
.bonus-log-item.unique-bonus { background-color: var(--wz-bg-medium); border-left: 5px solid var(--wz-accent-green); font-size: 1.1em; padding: 15px; text-align:center; }
.log-img-icon { width: 24px; height: 24px; object-fit: contain; vertical-align: middle; margin-right: 5px;}
.log-emoji-icon { font-size: 1.2em; vertical-align: middle; margin-right: 5px;}
.bonus-log-item { display: flex; flex-direction: column; align-items: center; gap: 10px; font-size: 0.95em; background-color: var(--wz-bg-light); padding: 10px 15px; margin-bottom: 8px; border-radius: 4px; border-left: 4px solid var(--wz-accent-cyan); }
.bonus-mod { color: var(--wz-text-medium); margin: 0 5px; font-style: italic;}
.player-name { font-weight: bold; color: var(--wz-accent-yellow); }
.points-awarded { font-weight: bold; color: var(--wz-accent-green); display:block; margin-top: 5px; }
.results-table { width: 100%; border-collapse: collapse; margin-top: 20px; box-shadow: 0 0 15px rgba(0,0,0,0.3); }
.results-table th, .results-table td { padding: 10px 12px; text-align: left; border-bottom: 1px solid var(--wz-border-color); font-size:0.9em;}
.results-table thead th { background-color: var(--wz-bg-light); color: var(--wz-accent-cyan); text-transform: uppercase; font-size: 0.85em; letter-spacing: 1px; }
.results-table td { color: var(--wz-text-medium); }
.results-table td:first-child { font-weight: bold; color: var(--wz-text-light); text-align:center; width: 60px;}
.results-table td:nth-child(2) { font-weight: bold; color: var(--wz-accent-yellow); }
.results-table td strong { font-size: 1.1em; color: var(--wz-text-light); }
.results-table tbody tr:hover { background-color: rgba(255, 255, 255, 0.05); }
.winner-row td { background-color: rgba(76, 175, 80, 0.25) !important; color: #fff !important; font-weight: bold; }
.winner-row td:nth-child(2) { color: var(--wz-accent-green) !important; }
.overall-winner-announce { text-align: center; font-size: 1.5em; color: var(--wz-accent-green); margin-top: 30px; padding: 15px; background-color: var(--wz-bg-medium); border-radius: 5px; }
.overall-winner-announce strong { color: var(--wz-accent-yellow); text-transform: uppercase; }
.mario-party-graph-section { margin-top: 30px; }
.mario-party-graph-section h2 { color: var(--wz-accent-yellow); }
.chart-container { min-height: 350px; padding: 10px; background-color: rgba(0,0,0,0.2); border-radius: 6px; border: 1px solid var(--wz-border-color); }
.navigation-actions { margin-top: 30px; text-align: center; }
.action-btn { display: inline-flex; align-items: center; justify-content: center; gap: 10px; color: var(--wz-text-dark); padding: 12px 22px; border: none; border-radius: 5px; cursor: pointer; margin: 0 10px; font-size: 1em; text-transform: uppercase; font-weight: bold; letter-spacing: 1.2px; transition: all 0.2s ease-in-out; text-decoration: none; background-color: var(--wz-accent-cyan); }
.action-btn:hover { background-color: #29deef; transform: translateY(-2px); }
hr { border: 0; height: 1px; background: var(--wz-border-color); margin: 30px 0; }

.completed-mk-visuals-results { margin-top: 20px; }
.stats-and-map-grid-results { display: grid; grid-template-columns: minmax(0, 2.5fr) minmax(0, 1fr); gap: 20px; align-items: flex-start; }
@media (max-width: 1200px) { .stats-and-map-grid-results { grid-template-columns: 1fr; } } /* La carte passe en dessous sur plus petits écrans */
.detailed-stats-section-results h3, .map-section-container-results h3 { color: var(--wz-accent-yellow); text-align: center; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 20px; font-size: 1.4em; }
.detailed-stats-section-results h4 { color: var(--wz-accent-cyan); font-size: 1.1em; margin-top: 20px; margin-bottom: 10px; }
.table-responsive { overflow-x: auto; background-color: rgba(0,0,0,0.15); padding: 10px; border-radius: 6px; border: 1px solid var(--wz-border-color); }
.detailed-summary-table {width: 100%; border-collapse:separate; border-spacing: 0;}
.detailed-summary-table td, .detailed-summary-table th { padding: 8px 10px; white-space: nowrap; font-size: 0.85em; text-align: center; }
.detailed-summary-table td:first-child, .detailed-summary-table th:first-child { min-width: 120px; text-align: left; position: sticky; left: 0; background-color: var(--wz-bg-medium); z-index: 1; }
.detailed-summary-table th:first-child { z-index: 2; }
.detailed-summary-table strong { font-size: 1.1em; color: var(--wz-text-light); }

.map-section-container-results { padding:15px; background-color: rgba(0,0,0,0.15); border-radius: 6px; border: 1px solid var(--wz-border-color); }
@media (min-width: 1201px) { .map-section-container-results { position: sticky; top: 80px; } }
.location-selector-mk-results { width: 100%; text-align: center; margin-bottom: 10px; }
.location-selector-mk-results label { margin-right: 10px; color: var(--wz-text-medium); }
.location-selector-mk-results select { padding: 8px 10px; background-color: var(--wz-bg-input); color: var(--wz-text-light); border: 1px solid var(--wz-border-color); border-radius: 4px; min-width: 220px; }
.map-container-mk-results { position: relative; width: 100%; max-width: 400px; border: 2px solid var(--wz-border-color); border-radius: 4px; overflow: hidden; margin: 0 auto; aspect-ratio: 1 / 1; }
.map-background-image-results { display: block; width: 100%; height: 100%; object-fit: cover; }
.map-point-results { position: absolute; width: 10px; height: 10px; background-color: var(--wz-accent-red); border: 1px solid white; border-radius: 50%; transform: translate(-50%, -50%); box-shadow: 0 0 6px black; font-size: 0.7em; display: flex; align-items: center; justify-content: center; color: white; font-weight: bold; z-index: 10; }
.game-spawn-point { background-color: var(--wz-accent-cyan); opacity: 0.8; width:12px; height:12px; }
.selected-spawn-point { background-color: gold; border-color: black; width: 14px; height: 14px; z-index: 11; font-size: 1em; }
.details-grid.summary-info-results { margin-bottom: 20px; }
.details-grid.summary-info-results p { margin-bottom: 5px; font-size: 1em; }
</style>