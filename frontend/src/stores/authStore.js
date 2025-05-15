// frontend/src/stores/authStore.js
import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import apiClient from '@/services/apiClient'; 
import router from '@/router'; // Importer le routeur

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('authToken') || null);
  const userData = ref(JSON.parse(localStorage.getItem('userData')) || null);

  const isAuthenticated = computed(() => !!token.value);

  function setToken(newToken) {
    token.value = newToken;
    if (newToken) {
      localStorage.setItem('authToken', newToken);
      // L'intercepteur de apiClient gère l'ajout du header
    } else {
      localStorage.removeItem('authToken');
      // L'intercepteur ne trouvera plus de token
    }
  }

  function setUserData(newUserData) {
    userData.value = newUserData;
    if (newUserData) {
      localStorage.setItem('userData', JSON.stringify(newUserData));
    } else {
      localStorage.removeItem('userData');
    }
  }

  async function login(credentials) {
    // La fonction de login est maintenant dans le store
    const loginResponse = await apiClient.post('/auth/login/', credentials);
    if (loginResponse.data.token) {
      setToken(loginResponse.data.token);
      try {
        const userDetailsResponse = await apiClient.get('/users/me/');
        setUserData(userDetailsResponse.data);
      } catch (userError) {
        console.error("Erreur récupération détails utilisateur après login:", userError);
        setUserData(null); // Effacer les données utilisateur en cas d'échec
      }
      return true; // Succès
    }
    return false; // Échec
  }

  function logout() {
    setToken(null);
    setUserData(null);
  }

  async function checkAuthStatus() {
     const storedToken = localStorage.getItem('authToken');
     if (storedToken) {
         token.value = storedToken; 
         try {
             const userDetailsResponse = await apiClient.get('/users/me/');
             setUserData(userDetailsResponse.data);
         } catch (error) {
             console.error("Token invalide ou session expirée au démarrage, déconnexion:", error);
             logout(); // Le token est invalide, déconnecter
             router.push({ name: 'login' }); 
         }
     } else {
         token.value = null; 
         userData.value = null;
     }
  }

  return { token, userData, isAuthenticated, login, logout, setUserData, setToken, checkAuthStatus };
});