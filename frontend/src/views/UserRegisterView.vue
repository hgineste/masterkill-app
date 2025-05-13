<script setup>
import { ref } from 'vue';
// MODIFIÉ: Importer apiClient
import apiClient from '@/services/apiClient'; // Assurez-vous que ce chemin est correct
import { useRouter, RouterLink } from 'vue-router'; // RouterLink si utilisé dans le template
import logoWarzone from '@/assets/images/logo-warzone.png';

const router = useRouter();

const formData = ref({
  username: '',
  // email: '', // Conservé commenté car vous avez simplifié pour username/password uniquement
  // first_name: '',
  // last_name: '',
  password: '',
  password_confirm: '',
});

const errorMessage = ref(null);
const successMessage = ref(null);
const isLoading = ref(false);

async function handleRegister() {
  isLoading.value = true;
  errorMessage.value = null;
  successMessage.value = null;

  if (formData.value.password !== formData.value.password_confirm) {
    errorMessage.value = "Les mots de passe ne correspondent pas.";
    isLoading.value = false;
    return;
  }

  if (!formData.value.username || !formData.value.password) {
    errorMessage.value = "Nom d'utilisateur et mot de passe sont requis.";
    isLoading.value = false;
    return;
  }

  try {
    const payload = {
      username: formData.value.username,
      password: formData.value.password,
      password_confirm: formData.value.password_confirm,
      // Si votre UserRegistrationSerializer backend s'attend à plus de champs (comme email, first_name)
      // et que vous voulez les collecter à nouveau, décommentez-les ici et dans formData.
      // email: formData.value.email, 
      // first_name: formData.value.first_name,
      // last_name: formData.value.last_name,
    };
    
    // MODIFIÉ: Utiliser apiClient et une URL relative
    await apiClient.post('/auth/register/', payload);

    successMessage.value = "Compte créé avec succès ! Vous pouvez maintenant vous connecter.";
    // Réinitialiser uniquement les champs utilisés pour la création simplifiée
    formData.value = { username: '', password: '', password_confirm: '', email: '', first_name: '', last_name: '' };
    
    setTimeout(() => {
      router.push({ name: 'login' });
    }, 2000);

  } catch (error) {
    if (error.response && error.response.data) {
      let errors = [];
      for (const key in error.response.data) {
        if (Array.isArray(error.response.data[key])) {
          errors.push(`${key}: ${error.response.data[key].join(', ')}`);
        } else {
          errors.push(`${key}: ${error.response.data[key]}`);
        }
      }
      errorMessage.value = errors.join(' ');
    } else {
      errorMessage.value = "Erreur lors de la création du compte. Veuillez réessayer.";
    }
    console.error("Erreur d'inscription:", error);
  } finally {
    isLoading.value = false;
  }
}
</script>

<template>
  <div class="register-view">
    <header class="page-header">
      <img :src="logoWarzone" alt="Warzone Logo" class="warzone-logo">
      <h1>Création de Compte Opérateur</h1>
    </header>
    <div class="content-wrapper-form register-form-container">
      <form @submit.prevent="handleRegister" class="auth-form">
        <h2>Rejoindre les rangs</h2>
        <div class="form-grid">
            <div class="form-group">
              <label for="username">Nom d'opérateur (Username) :</label>
              <input type="text" id="username" v-model.trim="formData.username" required autocomplete="username">
            </div>
            <div class="form-group">
              <label for="password">Mot de passe :</label>
              <input type="password" id="password" v-model="formData.password" required autocomplete="new-password">
            </div>
            <div class="form-group">
              <label for="password_confirm">Confirmer le mot de passe :</label>
              <input type="password" id="password_confirm" v-model="formData.password_confirm" required autocomplete="new-password">
            </div>
        </div>

        <div v-if="errorMessage" class="error-message form-error">
          {{ errorMessage }}
        </div>
        <div v-if="successMessage" class="success-message form-success">
          {{ successMessage }}
        </div>

        <button type="submit" class="submit-button main-action-button" :disabled="isLoading">
          {{ isLoading ? 'Création en cours...' : 'Créer le Compte' }}
        </button>
        <p class="form-link">
          Déjà un compte ? <RouterLink :to="{ name: 'login' }">Se connecter</RouterLink>
        </p>
      </form>
    </div>
  </div>
</template>

<style scoped>
/* Vos styles existants pour .register-view, .page-header, etc. restent les mêmes. */
/* Assurez-vous que .form-grid et .form-group s'adaptent bien à moins de champs. */
/* Les styles que vous aviez sont déjà assez génériques pour s'adapter. */

.register-view {
  min-height: 100vh;
  font-family: "Agency FB", "Roboto Condensed", Arial, sans-serif;
  background-color: var(--wz-bg-dark);
  background-image: linear-gradient(rgba(16, 16, 16, 0.9), rgba(16, 16, 16, 0.97)), url('@/assets/images/logo-warzone.png');
  background-size: cover; background-position: center center; background-attachment: fixed;
  color: var(--wz-text-light);
  padding-top: 0;
  padding-bottom: 40px;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.page-header {
  width: 100%;
  background-color: rgba(0,0,0,0.6); padding: 20px; text-align: center;
  border-bottom: 3px solid var(--wz-accent-yellow); margin-bottom: 40px;
}
.warzone-logo { max-height: 70px; margin-bottom: 15px; }
.page-header h1 {
  color: var(--wz-text-light); font-size: 2.2em; text-transform: uppercase;
  letter-spacing: 3px; margin: 0; font-weight: 700;
}

.register-form-container {
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

.form-grid {
    display: grid;
    grid-template-columns: 1fr; 
    gap: 0 20px; 
}

.form-group {
  margin-bottom: 20px;
}
.form-group label {
  display: block; margin-bottom: 8px; font-weight: normal;
  color: var(--wz-text-medium); font-size: 0.9em; text-transform: uppercase; letter-spacing: 0.5px;
}
.form-group input[type="text"],
.form-group input[type="email"], /* Garder le style même si email n'est plus là, pour cohérence future */
.form-group input[type="password"] {
  width: 100%; padding: 12px 15px; border: 1px solid #454545;
  background-color: var(--wz-bg-dark); color: var(--wz-text-light);
  border-radius: 4px; box-sizing: border-box; font-size: 1em;
  transition: border-color 0.3s, box-shadow 0.3s;
}
.form-group input[type="text"]:focus,
.form-group input[type="email"]:focus,
.form-group input[type="password"]:focus {
  border-color: var(--wz-accent-yellow); outline: none;
  box-shadow: 0 0 8px rgba(255, 193, 7, 0.5);
}

.submit-button.main-action-button {
  display: block; width: 100%;
  color: var(--wz-text-dark); 
  padding: 12px 20px; border: none; border-radius: 5px;
  cursor: pointer; margin-top: 10px; margin-bottom: 20px;
  font-size: 1.1em; text-transform: uppercase; font-weight: bold;
  letter-spacing: 1.5px; transition: all 0.2s ease-in-out;
  background-color: var(--wz-accent-yellow); 
}
.submit-button.main-action-button:hover:not(:disabled) {
  background-color: #ffdb58; 
  transform: translateY(-2px);
}
.submit-button.main-action-button:disabled {
  background-color: #555;
  color: #aaa;
  cursor: not-allowed;
}

.error-message.form-error, .success-message.form-success {
  margin-top: 15px; margin-bottom:15px;
  border: 1px solid;
  padding: 10px 15px;
  border-radius: 4px;
  font-size: 0.9em;
  text-align: center;
}
.error-message.form-error {
  color: var(--wz-text-light);
  background-color: var(--wz-accent-red);
  border-color: #c00;
}
.success-message.form-success {
  color: var(--wz-bg-dark); 
  background-color: var(--wz-accent-green-light); 
  border-color: var(--wz-accent-green);
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

:root {
    /* ... vos variables existantes ... */
    --wz-accent-green-light: #d4edda; /* Assurez-vous que cette variable est définie */
}
</style>