// frontend/src/services/apiClient.js

import axios from 'axios';

// Création d'une instance Axios avec une configuration de base
const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api', // Lit l'URL de base depuis les variables d'environnement
  // Vous pouvez ajouter d'autres configurations par défaut ici si nécessaire, comme un timeout :
  // timeout: 10000,
});

// Intercepteur de requête :
// Cette fonction sera appelée AVANT chaque requête envoyée avec 'apiClient'.
apiClient.interceptors.request.use(
  (config) => {
    // Récupérer le token depuis localStorage (ou votre store d'état plus tard)
    const token = localStorage.getItem('authToken');
    if (token) {
      // Si un token existe, l'ajouter à l'en-tête Authorization
      config.headers.Authorization = `Token ${token}`;
    }
    return config; // Renvoyer la configuration modifiée pour que la requête puisse continuer
  },
  (error) => {
    // Gérer les erreurs de configuration de requête
    return Promise.reject(error);
  }
);

// Optionnel : Intercepteur de réponse pour gérer les erreurs globalement (ex: déconnexion sur erreur 401)
// apiClient.interceptors.response.use(
//   response => response, // Simplement retourner la réponse si tout va bien
//   error => {
//     if (error.response && error.response.status === 401) {
//       // Si on reçoit une erreur 401 (Non autorisé), le token est peut-être invalide/expiré.
//       console.error("Erreur 401: Non autorisé. Déconnexion...");
//       localStorage.removeItem('authToken');
//       localStorage.removeItem('userData');
//       delete apiClient.defaults.headers.common['Authorization']; // Assurer la propreté
//       // Rediriger vers la page de connexion. Attention aux boucles si cette page fait aussi des appels.
//       // Il est préférable de gérer cela via le router ou un store.
//       // Pour l'instant, on logue juste l'erreur.
//       // window.location.href = '/login'; // Redirection plus brutale
//     }
//     return Promise.reject(error);
//   }
// );

export default apiClient; // Exporter l'instance configurée