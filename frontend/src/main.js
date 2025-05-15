// frontend/src/main.js
import { createApp } from 'vue'
import { createPinia } from 'pinia' // Importer createPinia
import App from './App.vue'
import router from './router'
import apiClient from './services/apiClient'; 

import './assets/main.css'

const app = createApp(App)
const pinia = createPinia() // Créer l'instance Pinia

app.use(pinia) // Utiliser Pinia
app.use(router)

// Importer et appeler checkAuthStatus après que Pinia soit initialisé et le router prêt
import { useAuthStore } from './stores/authStore';

router.isReady().then(async () => {
    const authStore = useAuthStore();
    await authStore.checkAuthStatus(); // Vérifier l'état d'auth au démarrage
    app.mount('#app');
});