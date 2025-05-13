<script setup>
import { ref, onMounted } from 'vue';
// MODIFIÉ: Importer apiClient
import apiClient from '@/services/apiClient'; // Assurez-vous que ce chemin est correct
import logoWarzone from '@/assets/images/logo-warzone.png'; // Si utilisé dans le template de cette vue

const gages = ref([]);
const isLoading = ref(true);
const error = ref(null);

onMounted(async () => {
  try {
    // MODIFIÉ: Utiliser apiClient et une URL relative
    const response = await apiClient.get('/gages/');
    gages.value = response.data;
  } catch (err) {
    console.error("Erreur lors de la récupération des gages:", err);
    error.value = "Impossible de charger les gages.";
  } finally {
    isLoading.value = false;
  }
});
</script>

<template>
  <div class="home-view">
    <header class="page-header">
      <img :src="logoWarzone" alt="Warzone Logo" class="warzone-logo">
      <h1>ACCUEIL MASTERKILL TRACKER</h1>
    </header>
    <div class="content-wrapper-simple">
      <h2>Liste des Gages (Exemple API)</h2>
      <div v-if="isLoading">
        <p>Chargement des gages...</p>
      </div>
      <div v-else-if="error" class="error-message">
        <p>{{ error }}</p>
      </div>
      <ul v-else-if="gages.length > 0" class="gage-list-home">
        <li v-for="gage in gages" :key="gage.id">
          {{ gage.text }}
        </li>
      </ul>
      <p v-else>Aucun gage trouvé.</p>
    </div>
  </div>
</template>

<style scoped>
/* Styles cohérents avec le thème */
.home-view {
  min-height: calc(100vh - 120px); /* Ajuster si header/footer ont des tailles différentes */
  font-family: "Agency FB", "Roboto Condensed", Arial, sans-serif;
  background-color: var(--wz-bg-dark);
  background-image: linear-gradient(rgba(16, 16, 16, 0.88), rgba(16, 16, 16, 0.96)), url('@/assets/images/map-background.jpg');
  background-size: cover; background-position: center center; background-attachment: fixed;
  color: var(--wz-text-light);
  padding-bottom: 20px;
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
.content-wrapper-simple {
  max-width: 800px; margin: 0 auto;
  background-color: rgba(30, 30, 30, 0.9); 
  padding: 30px; border-radius: 8px;
  box-shadow: 0 5px 25px rgba(0,0,0,0.7);
}
.content-wrapper-simple h2 {
  color: var(--wz-accent-cyan);
  text-align: center;
  margin-top: 0;
  margin-bottom: 25px;
  border-bottom: 1px solid var(--wz-border-color);
  padding-bottom: 10px;
}
.gage-list-home {
  list-style: none;
  padding: 0;
}
.gage-list-home li {
  background-color: var(--wz-bg-light);
  padding: 10px 15px;
  margin-bottom: 8px;
  border-radius: 4px;
  border-left: 3px solid var(--wz-accent-yellow);
  color: var(--wz-text-medium);
}
.loading, .error-message { text-align: center; padding: 20px; color: var(--wz-text-medium); }
.error-message { color: var(--wz-text-dark); background-color: var(--wz-accent-red); border: 1px solid #c00;}
</style>