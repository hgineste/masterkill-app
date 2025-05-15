<script setup>
import { ref } from 'vue';
import apiClient from '@/services/apiClient'; // Assurez-vous que ce chemin est correct
import { useRouter } from 'vue-router';
import logoWarzone from '@/assets/images/logo-warzone.png';

const router = useRouter();

const username = ref('');
const password = ref('');
const errorMessage = ref(null);
const isLoading = ref(false);

async function handleLogin() {
  isLoading.value = true;
  errorMessage.value = null;
  try {
    const loginResponse = await apiClient.post('/auth/login/', {
      username: username.value,
      password: password.value,
    });

    if (loginResponse.data.token) {
      localStorage.setItem('authToken', loginResponse.data.token);

      try {
        const userDetailsResponse = await apiClient.get('/users/me/');
        localStorage.setItem('userData', JSON.stringify(userDetailsResponse.data));
      } catch (userError) {
        console.error("Erreur lors de la récupération des détails utilisateur:", userError);
        localStorage.removeItem('userData');
      }
      
      router.push({ name: 'home' });
    } else {
      errorMessage.value = "Token non reçu de l'API après la connexion.";
    }
  } catch (error) {
    if (error.response && error.response.data) {
      errorMessage.value = error.response.data.non_field_errors?.join(', ') || "Nom d'utilisateur ou mot de passe incorrect.";
    } else if (error.request) {
      errorMessage.value = "Aucune réponse du serveur. Vérifiez votre connexion ou le serveur backend.";
    } else {
      errorMessage.value = "Erreur de connexion. Veuillez réessayer.";
    }
    console.error("Erreur de connexion:", error);
    localStorage.removeItem('authToken');
    localStorage.removeItem('userData');
  } finally {
    isLoading.value = false;
  }
}
</script>

<template>
  <div class="login-view">
    <header class="page-header">
      <img :src="logoWarzone" alt="Warzone Logo" class="warzone-logo">
      <h1>Accès Opérateur</h1>
    </header>
    <div class="content-wrapper-form login-form-container">
      <form @submit.prevent="handleLogin" class="auth-form">
        <h2>Connexion</h2>
        <div class="form-group">
          <label for="username">Nom d'opérateur (Username) :</label>
          <input type="text" id="username" v-model="username" required autocomplete="username">
        </div>
        <div class="form-group">
          <label for="password">Mot de passe :</label>
          <input type="password" id="password" v-model="password" required autocomplete="current-password">
        </div>
        <div v-if="errorMessage" class="error-message form-error">
          {{ errorMessage }}
        </div>
        <button type="submit" class="submit-button main-action-button" :disabled="isLoading">
          {{ isLoading ? 'Connexion en cours...' : 'Se Connecter' }}
        </button>
        <p class="form-link">
          Pas encore d'indicatif ? <RouterLink :to="{ name: 'register' }">Créer un compte</RouterLink>
        </p>
      </form>
    </div>
  </div>
</template>

<style scoped>
/* Styles similaires à CreateMasterkillEventView, adaptés pour le login */
.login-view {
  min-height: 100vh;
  font-family: "Agency FB", "Roboto Condensed", Arial, sans-serif;
  background-color: var(--wz-bg-dark);
  background-image: linear-gradient(rgba(16, 16, 16, 0.9), rgba(16, 16, 16, 0.97)), url('@/assets/images/logo-warzone.png'); /* Utilisez une image de fond appropriée */
  background-size: cover; background-position: center center; background-attachment: fixed;
  color: var(--wz-text-light);
  padding-top: 0; /* Ajuster pour que le header soit bien placé */
  padding-bottom: 40px;
  display: flex;
  flex-direction: column;
  align-items: center; /* Centrer le contenu global */
}

.page-header {
  width: 100%; /* Prendre toute la largeur */
  background-color: rgba(0,0,0,0.6); padding: 20px; text-align: center;
  border-bottom: 3px solid var(--wz-accent-yellow); margin-bottom: 40px; /* Augmenter marge */
}
.warzone-logo { max-height: 70px; margin-bottom: 15px; }
.page-header h1 {
  color: var(--wz-text-light); font-size: 2.2em; text-transform: uppercase;
  letter-spacing: 3px; margin: 0; font-weight: 700;
}


.login-form-container {
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

.auth-form h2 {
  text-align: center;
  color: var(--wz-accent-cyan);
  font-size: 1.8em;
  margin-bottom: 25px;
}

.form-group {
  margin-bottom: 20px;
}
.form-group label {
  display: block; margin-bottom: 8px; font-weight: normal;
  color: var(--wz-text-medium); font-size: 0.9em; text-transform: uppercase; letter-spacing: 0.5px;
}
.form-group input[type="text"],
.form-group input[type="password"] {
  width: 100%; padding: 12px 15px; border: 1px solid #454545;
  background-color: var(--wz-bg-dark); color: var(--wz-text-light);
  border-radius: 4px; box-sizing: border-box; font-size: 1em;
  transition: border-color 0.3s, box-shadow 0.3s;
}
.form-group input[type="text"]:focus,
.form-group input[type="password"]:focus {
  border-color: var(--wz-accent-yellow); outline: none;
  box-shadow: 0 0 8px rgba(255, 193, 7, 0.5);
}

.submit-button.main-action-button {
  display: block; width: 100%;
  color: white; /* Texte en blanc pour contraste avec fond vert */
  padding: 12px 20px; border: none; border-radius: 5px;
  cursor: pointer; margin-top: 10px; margin-bottom: 20px;
  font-size: 1.1em; text-transform: uppercase; font-weight: bold;
  letter-spacing: 1.5px; transition: all 0.2s ease-in-out;
  background-color: var(--wz-accent-green); /* Vert pour le bouton de connexion */
}
.submit-button.main-action-button:hover:not(:disabled) {
  background-color: #4cae4c; /* Vert plus foncé au survol */
  transform: translateY(-2px);
}
.submit-button.main-action-button:disabled {
  background-color: #555;
  cursor: not-allowed;
}

.error-message.form-error {
  margin-top: 15px; margin-bottom:15px;
  color: var(--wz-text-light); /* Texte clair pour fond rouge */
  background-color: var(--wz-accent-red);
  border: 1px solid #c00;
  padding: 10px;
  border-radius: 4px;
  font-size: 0.9em;
  text-align: center;
}
.form-link {
    text-align: center;
    margin-top: 20px;
    font-size: 0.9em;
}
.form-link a {
    color: var(--wz-accent-yellow);
    text-decoration: none;
    font-weight: bold;
}
.form-link a:hover {
    text-decoration: underline;
}
</style>