<script setup>
import { ref } from 'vue'
import { uploadScreenshot } from '@/services/gameApi'

const props = defineProps({ gameId: Number })
const emit  = defineEmits(['statsReady'])

const file = ref(null)
const loading = ref(false)
const error = ref(null)

async function send () {
  if (!file.value) return
  loading.value = true
  error.value = null
  try {
    const players = await uploadScreenshot(props.gameId, file.value)
    emit('statsReady', players)
  } catch (e) {
    error.value = e.response?.data?.detail || 'Erreur OCR'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="flex items-center gap-2 my-3">
    <input type="file" accept="image/*" @change="e => file.value = e.target.files[0]" />
    <button class="btn btn-primary" :disabled="!file || loading" @click="send">
      {{ loading ? 'Analyse…' : 'Analyser' }}
    </button>
    <span v-if="error" class="text-red-500 text-sm">{{ error }}</span>
  </div>
</template>
