import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useAuthStore = defineStore('auth', () => {
  // API Key（用于访问后端）
  const apiKey = ref(localStorage.getItem('api_key') || '')
  
  // 最后验证时间
  const lastVerified = ref(localStorage.getItem('last_verified') || null)
  
  const isAuthenticated = computed(() => !!apiKey.value && !!lastVerified.value)
  
  function setApiKey(key) {
    apiKey.value = key
    localStorage.setItem('api_key', key)
  }
  
  function setVerified(timestamp) {
    lastVerified.value = timestamp
    localStorage.setItem('last_verified', timestamp)
  }
  
  function clearAuth() {
    apiKey.value = ''
    lastVerified.value = ''
    localStorage.removeItem('api_key')
    localStorage.removeItem('last_verified')
  }
  
  return {
    apiKey,
    lastVerified,
    isAuthenticated,
    setApiKey,
    setVerified,
    clearAuth
  }
})
