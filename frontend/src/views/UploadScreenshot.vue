<script setup>
import { ref } from 'vue'
import { useRoute } from 'vue-router'
import { uploadScreenshot } from '@/services/gameApi'

const route = useRoute()                         //  /game/:gameId?/upload
const gameId = route.params.gameId || null       // → si tu appelles sans paramètre, mets-le en dur

const file       = ref(null)
const isSending  = ref(false)
const errorMsg   = ref(null)
const ocrResults = ref([])                       // [{ gamertag, kills, revives }, …]

function handleFileChange (e) {
  errorMsg.value  = null
  ocrResults.value = []
  file.value       = e.target.files[0] || null
}

async function send () {
  if (!file.value) { errorMsg.value = 'Choisis d’abord une image.'; return }
  if (!gameId)     { errorMsg.value = 'gameId manquant dans l’URL.'; return }

  isSending.value = true
  errorMsg.value  = null
  try {
    const data = await uploadScreenshot(gameId, file.value)
    ocrResults.value = data           // assumé : tableau retourné par l’API
  } catch (err) {
    errorMsg.value = err.response?.data?.detail || err.message
  } finally {
    isSending.value = false
  }
}
</script>

<template>
  <div class="upload-page">
    <h1>Upload screenshot – OCR</h1>

    <input type="file" accept="image/*" @change="handleFileChange" />
    <button :disabled="isSending" @click="send">Envoyer</button>

    <p v-if="isSending">Envoi / OCR en cours…</p>
    <p v-if="errorMsg" class="error">{{ errorMsg }}</p>

    <div v-if="ocrResults.length">
      <h2>Résultats OCR</h2>
      <table>
        <thead><tr><th>Joueur</th><th>Kills</th><th>Réas</th></tr></thead>
        <tbody>
          <tr v-for="r in ocrResults" :key="r.gamertag">
            <td>{{ r.gamertag }}</td><td>{{ r.kills }}</td><td>{{ r.revives }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style scoped>
.upload-page { padding: 30px; max-width: 500px; margin:auto }
.error       { color: #c00 }
table { border-collapse: collapse; width:100% }
td,th{ border:1px solid #666; padding:4px; text-align:center }
</style>
