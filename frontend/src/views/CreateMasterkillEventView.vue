<script setup>
import { ref, onMounted } from 'vue';
// MODIFIÉ: Importer apiClient
import apiClient from '@/services/apiClient'; // Assurez-vous que ce chemin est correct
import { useRouter } from 'vue-router';
import logoWarzone from '@/assets/images/logo-warzone.png';

const router = useRouter();

const newMK = ref({
  name: 'Nouveau MK Warzone',
  num_games_planned: 3,
  points_kill: 1,
  points_rea: 1,
  points_redeploiement: -1,
  points_goulag_win: 1,
  points_rage_quit: -5,
  points_execution: 1,
  points_humiliation: -1,
  top1_solo_ends_mk: false,
  selected_gage_text: '',
});
const createError = ref(null);

const gameModes = ref([
  { text: 'Solo (1 joueur)', value: 1 },
  { text: 'Duo (2 joueurs)', value: 2 },
  { text: 'Trio (3 joueurs)', value: 3 },
  { text: 'Quatuor (4 joueurs)', value: 4 },
]);
const selectedPlayerCount = ref(2);
const playerNames = ref(['', '']);

const updatePlayerNameFields = (count) => {
  const num = parseInt(count);
  playerNames.value = Array(num).fill('');
};

onMounted(() => {
  updatePlayerNameFields(selectedPlayerCount.value);
});

async function handleCreateMasterkill() {
  createError.value = null;
  if (!newMK.value.name.trim()) {
    createError.value = "Le nom du Masterkill est requis.";
    return;
  }
  const validPlayerNames = playerNames.value.map(name => name.trim()).filter(name => name !== '');

  const payload = {
    name: newMK.value.name,
    num_games_planned: parseInt(newMK.value.num_games_planned) || 1,
    points_kill: parseInt(newMK.value.points_kill) || 0,
    points_rea: parseInt(newMK.value.points_rea) || 0,
    points_redeploiement: parseInt(newMK.value.points_redeploiement) || 0,
    points_goulag_win: parseInt(newMK.value.points_goulag_win) || 0,
    points_rage_quit: parseInt(newMK.value.points_rage_quit) || 0,
    points_execution: parseInt(newMK.value.points_execution) || 0,
    points_humiliation: parseInt(newMK.value.points_humiliation) || 0,
    top1_solo_ends_mk: newMK.value.top1_solo_ends_mk,
    participant_gamertags: validPlayerNames,
    custom_gage_input_text: newMK.value.selected_gage_text.trim() === '' ? null : newMK.value.selected_gage_text.trim(),
  };

  try {
    // MODIFIÉ: Utiliser apiClient et une URL relative
    const response = await apiClient.post('/masterkillevents/', payload);
    router.push({ name: 'masterkill-detail', params: { id: response.data.id } });
  } catch (err) {
    console.error("Erreur lors de la création du MK:", err);
    createError.value = "Erreur lors de la création du MK. ";
    if (err.response && err.response.data) {
      for (const key in err.response.data) {
        createError.value += `${key}: ${err.response.data[key].join ? err.response.data[key].join(', ') : err.response.data[key]} `;
      }
    } else {
      createError.value += err.message;
    }
  }
}
</script>

<template>
  <div class="create-masterkill-view">
    <header class="page-header">
      <img :src="logoWarzone" alt="Warzone Logo" class="warzone-logo">
      <h1>INITIALISER NOUVEL ÉVÉNEMENT MASTERKILL</h1>
    </header>
    <div class="content-wrapper-form">
      <div class="create-mk-form">
        <form @submit.prevent="handleCreateMasterkill">

          <div class="form-layout-grid">

            <div class="form-column-main">
              <div class="form-section">
                <div class="form-group">
                  <label for="mk-name">Nom de code du Masterkill :</label>
                  <input type="text" id="mk-name" v-model.trim="newMK.name" required placeholder="Ex: Opération Tonnerre">
                </div>
                <div class="form-group">
                  <label for="mk-gage">Gage de l'événement (optionnel) :</label>
                  <input type="text" id="mk-gage" v-model.trim="newMK.selected_gage_text" placeholder="Ex: Le perdant paie sa tournée">
                </div>
              </div>

              <div class="form-section layout-cols-2">
                <div class="form-group">
                  <label for="game-mode">Mode de Jeu (Effectif) :</label>
                  <select id="game-mode" v-model.number="selectedPlayerCount" @change="updatePlayerNameFields($event.target.value)">
                    <option v-for="mode in gameModes" :key="mode.value" :value="mode.value">
                      {{ mode.text }}
                    </option>
                  </select>
                </div>
                <div class="form-group">
                  <label for="mk-games">Nombre de Parties Prévues :</label>
                  <input type="number" id="mk-games" v-model.number="newMK.num_games_planned" min="1">
                </div>
              </div>

              <div v-if="selectedPlayerCount > 0" class="form-section">
                <h4 class="form-subtitle">IDENTIFICATION DES OPÉRATEURS :</h4>
                <div class="player-inputs-grid" :style="{'grid-template-columns': `repeat(${selectedPlayerCount > 2 ? 2 : selectedPlayerCount}, 1fr)`}">
                  <div v-for="(name, index) in playerNames" :key="index" class="form-group">
                    <label :for="'player-name-' + index">Opérateur {{ index + 1 }} :</label>
                    <input type="text" :id="'player-name-' + index" v-model.trim="playerNames[index]" placeholder="Gamertag">
                  </div>
                </div>
              </div>
            </div>

            <div class="form-column-secondary">
              <div class="form-section">
                <h4 class="form-subtitle">BARÈME DES POINTS D'ACTION :</h4>
                <div class="points-grid compact-points-grid">
                  <div class="form-group"><label for="mk-kill-points">Élimination :</label><input type="number" id="mk-kill-points" v-model.number="newMK.points_kill"></div>
                  <div class="form-group"><label for="mk-rea-points">Réanimation :</label><input type="number" id="mk-rea-points" v-model.number="newMK.points_rea"></div>
                  <div class="form-group"><label for="mk-redeploy-points">Redéploiement :</label><input type="number" id="mk-redeploy-points" v-model.number="newMK.points_redeploiement"></div>
                  <div class="form-group"><label for="mk-goulag-points">Goulag Gagné :</label><input type="number" id="mk-goulag-points" v-model.number="newMK.points_goulag_win"></div>
                  <div class="form-group"><label for="mk-rq-points">Rage Quit :</label><input type="number" id="mk-rq-points" v-model.number="newMK.points_rage_quit"></div>
                  <div class="form-group"><label for="mk-exec-points">Exécution :</label><input type="number" id="mk-exec-points" v-model.number="newMK.points_execution"></div>
                  <div class="form-group"><label for="mk-humiliation-points">Humiliation :</label><input type="number" id="mk-humiliation-points" v-model.number="newMK.points_humiliation"></div>
                </div>
              </div>

              <div class="form-section">
                <h4 class="form-subtitle">CONDITIONS SPÉCIALES :</h4>
                <div class="form-group form-group-checkbox">
                  <input type="checkbox" id="mk-top1-ends" v-model="newMK.top1_solo_ends_mk">
                  <label for="mk-top1-ends" class="checkbox-label">TOP 1 solo met fin au MK ?</label>
                </div>
              </div>
            </div>
          </div>

          <button type="submit" class="submit-button main-action-button"><span class="icon-play">▶</span> CRÉER ET LANCER MISSION</button>
          <div v-if="createError" class="error-message form-error">{{ createError }}</div>
        </form>
        </div>
    </div>
  </div>
</template>

<style scoped>
/* Styles (inchangés par rapport à votre version précédente) */
.create-masterkill-view {
  min-height: 100vh;
  font-family: "Agency FB", "Roboto Condensed", Arial, sans-serif;
  background-color: var(--wz-bg-dark);
  background-image: linear-gradient(rgba(16, 16, 16, 0.9), rgba(16, 16, 16, 0.97)), url('@/assets/images/logo-warzone.png');
  background-size: cover; background-position: center center; background-attachment: fixed;
  color: var(--wz-text-light);
  padding-bottom: 40px;
  box-sizing: border-box;
}

.page-header {
  background-color: rgba(0,0,0,0.6); padding: 20px; text-align: center;
  border-bottom: 3px solid var(--wz-accent-yellow); margin-bottom: 30px;
}
.warzone-logo { max-height: 70px; margin-bottom: 15px; }
.page-header h1 {
  color: var(--wz-text-light); font-size: 2.2em; text-transform: uppercase;
  letter-spacing: 3px; margin: 0; border-bottom: none; font-weight: 700;
}


.content-wrapper-form {
  width: 80vw;
  max-width: 1300px;
  min-width: 750px;
  margin-left: auto;
  margin-right: auto;
  background-color: rgba(30, 30, 30, 0.92);
  padding: 25px 30px;
  border-radius: 8px;
  box-shadow: 0 5px 25px rgba(0,0,0,0.7);
}

.form-layout-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 20px 40px;
}

@media (min-width: 992px) {
  .form-layout-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

.form-column-main, .form-column-secondary {
  display: flex;
  flex-direction: column;
  gap: 25px;
}

.form-section {
  margin-bottom: 0;
  padding-bottom: 20px;
  border-bottom: 1px dashed var(--wz-border-color);
}
.form-column-main .form-section:last-of-type,
.form-column-secondary .form-section:last-of-type {
  border-bottom: none;
  padding-bottom: 0;
}

.layout-cols-2 { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 20px; }
.player-inputs-grid { display: grid; gap: 15px; }

.points-grid.compact-points-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 15px 18px;
}

.form-group { margin-bottom: 20px; } /* Rétablir un peu de marge pour espacer les champs dans une section */
/* Retirer la marge du dernier form-group d'une section si elle a une bordure en bas */
.form-section > .form-group:last-child {
    margin-bottom: 0;
}

.form-group label { display: block; margin-bottom: 8px; font-weight: normal; color: var(--wz-text-medium); font-size: 0.9em; text-transform: uppercase; letter-spacing: 0.5px;}
.form-group input[type="text"],
.form-group input[type="number"],
.form-group select {
  width: 100%; padding: 10px 12px; border: 1px solid #454545;
  background-color: var(--wz-bg-dark); color: var(--wz-text-light);
  border-radius: 4px; box-sizing: border-box; font-size: 0.95em;
  transition: border-color 0.3s, box-shadow 0.3s;
}
.form-group input[type="text"]:focus,
.form-group input[type="number"]:focus,
.form-group select:focus {
  border-color: var(--wz-accent-yellow); outline: none;
  box-shadow: 0 0 8px rgba(255, 193, 7, 0.5);
}
.form-group-checkbox { display: flex; align-items: center; background-color: var(--wz-bg-light); padding: 10px 15px; border-radius: 4px; border: 1px solid var(--wz-border-color); margin-top:10px;}
.form-group input[type="checkbox"] { width: auto; height: 18px; width: 18px; margin-right: 10px; accent-color: var(--wz-accent-yellow); cursor: pointer; flex-shrink: 0; }
label.checkbox-label { font-weight: normal; color: var(--wz-text-light); margin-bottom: 0; cursor: pointer; font-size: 0.95em; text-transform: none; }
.form-subtitle { margin-top: 10px; margin-bottom: 15px; color: var(--wz-accent-cyan); border-bottom: none; font-size: 1.1em; text-transform: uppercase; letter-spacing: 0.8px; }

.main-action-button {
  display: flex; align-items: center; justify-content: center; gap: 10px;
  color: var(--wz-text-dark); padding: 14px 28px; border: none; border-radius: 5px;
  cursor: pointer; margin: 30px auto 0 auto;
  font-size: 1.15em; text-transform: uppercase; font-weight: bold;
  letter-spacing: 1.5px; transition: all 0.2s ease-in-out;
  box-shadow: 0 3px 7px rgba(0,0,0,0.4);
}
.submit-button.main-action-button { background-color: var(--wz-accent-green); color:white;}
.submit-button.main-action-button:hover { background-color: #4cae4c;  transform: translateY(-2px); box-shadow: 0 5px 10px rgba(0,0,0,0.5); }
.error-message.form-error { margin-top: 25px; color: var(--wz-text-dark); background-color: var(--wz-accent-red); border: 1px solid #c00;}
.icon-play, .icon-target { font-weight: bold; font-size: 1.2em; margin-right: 8px;}
</style>