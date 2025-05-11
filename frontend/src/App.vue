<script setup>
import { RouterView } from 'vue-router'
</script>

<template>
  <header>
    <div>
      <h1>Masterkill Tracker</h1>
    </div>
  </header>
  <main>
    <RouterView /> </main>
</template>

<style scoped>
/* Styles de base pour App.vue, vous pourrez les personnaliser */
header {
  line-height: 1.5;
  max-height: 100vh;
  padding: 1rem;
  border-bottom: 1px solid #ccc;
}
main {
  padding: 1rem;
}
</style>