<template>
  <div class="test-view">
    <h1>Test View</h1>
    <button @click="count++">Count: {{ count }}</button>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const count = ref(0)
</script>

<style scoped>
.test-view {
  padding: 20px;
  text-align: center;
}
</style>
