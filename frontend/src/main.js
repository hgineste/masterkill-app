import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import axios from 'axios'

import './assets/main.css' 

const token = localStorage.getItem('authToken');
if (token) {
  axios.defaults.headers.common['Authorization'] = `Token ${token}`;
}

const app = createApp(App)
app.use(router)

app.mount('#app')