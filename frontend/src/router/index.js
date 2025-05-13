// Fichier: src/router/index.js
import { createRouter, createWebHistory } from 'vue-router';
import MasterkillEventsListView from '../views/MasterkillEventsListView.vue';
import CreateMasterkillEventView from '../views/CreateMasterkillEventView.vue';
import ClassementView from '../views/ClassementView.vue';
import MKDetailView from '../views/MKDetailView.vue';
import MKResultsView from '../views/MKResultsView.vue';
import UserLoginView from '../views/UserLoginView.vue';
import UserRegisterView from '../views/UserRegisterView.vue'; // Supposons que ce composant est maintenant créé

// Placeholders (si encore utilisés pour certaines routes)
const PlayerProfileView = { template: '<div class="placeholder-view"><h1>Profil Joueur</h1><p>(Contenu à venir)</p><router-link to="/">Retour Accueil</router-link></div>' };
const ActiveGameView = { template: '<div class="placeholder-view"><h1>Partie en Cours</h1><p>(Interface de saisie à venir)</p><router-link to="/">Retour Accueil</router-link></div>' };

const routes = [
  {
    path: '/',
    name: 'home',
    component: MasterkillEventsListView,
    meta: { requiresAuth: true } // Cette page nécessite d'être connecté
  },
  {
    path: '/masterkills/create',
    name: 'create-masterkill',
    component: CreateMasterkillEventView,
    meta: { requiresAuth: true } // Nécessite d'être connecté
  },
  {
    path: '/masterkill/:id',
    name: 'masterkill-detail',
    component: MKDetailView,
    props: true,
    meta: { requiresAuth: true } // Nécessite d'être connecté
  },
  {
    path: '/classement',
    name: 'classement',
    component: ClassementView,
    meta: { requiresAuth: true } // Nécessite d'être connecté
  },
  {
    path: '/player/:playerId',
    name: 'player-profile',
    component: PlayerProfileView,
    props: true,
    meta: { requiresAuth: true } // Nécessite d'être connecté
  },
  {
    path: '/login',
    name: 'login',
    component: UserLoginView,
    meta: { guestOnly: true } // Seulement pour les non-connectés
  },
  {
    path: '/register',
    name: 'register',
    component: UserRegisterView, // Assurez-vous que ce composant existe
    meta: { guestOnly: true } // Seulement pour les non-connectés
  },
  {
    path: '/game/:gameId/live',
    name: 'active-game',
    component: ActiveGameView,
    props: true,
    meta: { requiresAuth: true } // Nécessite d'être connecté
  },
  {
    path: '/masterkill/:id/results',
    name: 'masterkill-results',
    component: MKResultsView,
    props: true,
    meta: { requiresAuth: true } // Nécessite d'être connecté
  },
];

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes
});

router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('authToken');
  const isAuthenticated = !!token; // true si token existe et n'est pas une chaîne vide

  // Logs pour le débogage
  console.log('------------------------------------');
  console.log('Navigation Guard Triggered');
  console.log('From:', from.name || from.path, 'To:', to.name || to.path);
  console.log('Token in localStorage:', token);
  console.log('Calculated isAuthenticated:', isAuthenticated);
  console.log('To route meta:', to.meta);

  if (to.meta.requiresAuth && !isAuthenticated) {
    console.log('Decision: Route requires auth, user NOT authenticated. Redirecting to LOGIN.');
    next({ name: 'login' });
  } else if (to.meta.guestOnly && isAuthenticated) {
    console.log('Decision: Route is guestOnly, user IS authenticated. Redirecting to HOME.');
    next({ name: 'home' });
  } else {
    console.log('Decision: Allowing navigation.');
    next();
  }
  console.log('------------------------------------');
});

export default router;