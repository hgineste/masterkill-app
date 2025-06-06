<script setup>
import { RouterLink, RouterView, useRouter } from 'vue-router';
import { computed, ref, onMounted, onUnmounted } from 'vue'; // Ajout de ref, onMounted, onUnmounted

const router = useRouter();

// Une clé réactive simple. Changer sa valeur forcera la réévaluation
// des computed properties qui en dépendent.
const navUpdateTrigger = ref(0);

const isAuthenticated = computed(() => {
  // On accède à navUpdateTrigger.value pour rendre ce computed dépendant de lui.
  // Même si on n'utilise pas directement sa valeur dans le return,
  // le simple fait de l'accéder crée la dépendance réactive.
  // eslint-disable-next-line no-unused-expressions
  navUpdateTrigger.value; 

  const token = localStorage.getItem('authToken');
  console.log('App.vue - isAuthenticated computed. Token:', token, 'Trigger:', navUpdateTrigger.value); // Pour débogage
  return !!token;
});

function handleLogout() {
  localStorage.removeItem('authToken');
  localStorage.removeItem('userData');
  navUpdateTrigger.value++; // Déclencher une mise à jour de la nav
  router.push({ name: 'login' });
}

// Variable pour stocker la fonction de désinscription du hook de navigation
let unregisterAfterEachHook = null;

onMounted(() => {
  // Ce hook s'exécutera APRÈS chaque navigation réussie.
  unregisterAfterEachHook = router.afterEach((to, from) => {
    console.log('App.vue - router.afterEach: Navigation vers', to.name, 'terminée. Mise à jour du trigger.');
    navUpdateTrigger.value++; // Incrémenter pour forcer la réévaluation de isAuthenticated
  });
  // Forcer une évaluation initiale au cas où on arrive sur la page avec un token déjà là
  // (par exemple après un rechargement manuel) et que la nav ne s'est pas mise à jour via le cycle de vie initial.
  navUpdateTrigger.value++;
});

onUnmounted(() => {
  // Nettoyer le hook si App.vue est un jour démonté (peu probable pour le composant racine)
  if (unregisterAfterEachHook) {
    unregisterAfterEachHook();
  }
});
</script>

<template>
  <div id="app-wrapper">
    <nav class="global-nav">
      <RouterLink :to="{ name: 'home' }">Accueil</RouterLink>
      <template v-if="isAuthenticated">
        <RouterLink :to="{ name: 'create-masterkill' }">Créer un MK</RouterLink>
        <RouterLink :to="{ name: 'classement' }">Classement</RouterLink>
        <button @click="handleLogout" class="nav-button logout-button">Déconnexion</button>
      </template>
      <template v-else>
        <RouterLink :to="{ name: 'login' }">Connexion</RouterLink>
        <RouterLink :to="{ name: 'register' }">Inscription</RouterLink>
      </template>
    </nav>
    <main class="main-container">
      <RouterView />
    </main>
    <footer class="global-footer">
      <p>&copy; {{ new Date().getFullYear() }} Masterkill Tracker</p>
    </footer>
  </div>
</template>

<style> /* Styles globaux (non scopés) */
@import url('https://fonts.googleapis.com/css2?family=Roboto+Condensed:wght@400;700&family=Russo+One&display=swap');

:root {
  --wz-bg-dark: #101010;
  --wz-bg-medium: #1e1e1e;
  --wz-bg-light: #2c2c2c;
  --wz-text-light: #f0f0f0;
  --wz-text-medium: #c0c0c0;
  --wz-text-dark: #101010; /* Pour texte sur fond clair */
  --wz-accent-yellow: #ffc107;
  --wz-accent-cyan: #00bcd4;
  --wz-accent-green: #4CAF50;
  --wz-accent-red: #f44336;
  --wz-border-color: #3a3a3a;
}

html {
  box-sizing: border-box;
}
*, *:before, *:after {
  box-sizing: inherit;
}

body {
  font-family: "Agency FB", "Roboto Condensed", Arial, sans-serif;
  margin: 0;
  background-color: #101010;
  color: var(--wz-text-light);
  line-height: 1.6;
}

#app-wrapper { /* Assurez-vous que c'est bien l'ID de votre div racine dans App.vue */
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background-color: var(--wz-bg-dark); /* AJOUTÉ : Assure que le conteneur principal est sombre */
}

.global-nav {
  background-color: rgba(0,0,0,0.85);
  padding: 12px 25px;
  text-align: center;
  border-bottom: 2px solid var(--wz-accent-yellow);
  box-shadow: 0 2px 10px rgba(0,0,0,0.5);
  position: sticky;
  top: 0;
  z-index: 1000;
  display: flex;
  justify-content: center;
  align-items: center;
  flex-wrap: wrap; /* Permettre le retour à la ligne sur petits écrans */
}
.global-nav a, .nav-button {
  color: var(--wz-accent-yellow);
  margin: 5px 12px; /* Ajout de marge verticale pour le wrapping */
  padding: 8px 10px;
  text-decoration: none;
  font-weight: bold;
  text-transform: uppercase;
  letter-spacing: 1px;
  transition: color 0.3s ease, transform 0.2s ease, background-color 0.3s ease;
  font-family: 'Russo One', sans-serif;
  font-size: 0.9em;
  border-radius: 4px;
  background-color: transparent; /* Pour les boutons */
  border: none; /* Pour les boutons */
  cursor: pointer; /* Pour les boutons */
}
.global-nav a:hover, .nav-button:hover {
  color: var(--wz-text-dark);
  background-color: var(--wz-accent-yellow);
  transform: scale(1.05);
}
.global-nav a.router-link-exact-active {
  color: var(--wz-text-dark);
  background-color: var(--wz-accent-cyan);
  box-shadow: 0 0 10px var(--wz-accent-cyan);
}
.logout-button { /* Style spécifique si différent de .nav-button général */
    background-color: var(--wz-accent-red) !important; /* Important pour surcharger si besoin */
    color: white !important;
}
.logout-button:hover {
    background-color: #c82333 !important; /* Rouge plus foncé */
    color: white !important;
}


.main-container {
  flex-grow: 1;
  /* Optionnel : Si vous voulez que la zone de contenu ait aussi ce fond par défaut */
  /* background-color: var(--wz-bg-dark); */
  /* Un padding ici pourrait créer l'effet de "fond blanc autour" si les composants internes n'ont pas de fond */
}

.global-footer {
  background-color: rgba(0,0,0,0.85);
  color: var(--wz-text-medium);
  text-align: center;
  padding: 15px;
  font-size: 0.85em;
  border-top: 1px solid var(--wz-border-color);
}

.placeholder-view {
  min-height: 70vh; display: flex; flex-direction: column;
  justify-content: center; align-items: center;
  padding: 20px; text-align: center;
  font-family: "Agency FB", "Roboto Condensed", Arial, sans-serif;
  /* Le placeholder a déjà son propre fond sombre et image */
  /* background-color: var(--wz-bg-dark); */
  /* background-image: linear-gradient(rgba(16, 16, 16, 0.88), rgba(16, 16, 16, 0.96)), url('@/assets/images/map-background.jpg'); */
  /* background-size: cover; background-position: center center; background-attachment: fixed; */
  color: var(--wz-text-light);
}
.placeholder-view h1 { color: var(--wz-accent-yellow); margin-bottom: 20px; }
.placeholder-view p { color: var(--wz-text-medium); margin-bottom: 20px; }
.placeholder-view a { color: var(--wz-accent-cyan); text-decoration: none; font-weight: bold; }
.placeholder-view a:hover { text-decoration: underline; }
</style>