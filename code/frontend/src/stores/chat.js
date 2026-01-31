import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useChatStore = defineStore('chat', () => {
  const messages = ref([])
  const isLoading = ref(false)
  const isListening = ref(false)
  const currentTranscript = ref('')
  
  function addMessage(role, content) {
    messages.value.push({
      role,
      content,
      timestamp: Date.now()
    })
  }
  
  function setListening(status) {
    isListening.value = status
  }
  
  function setTranscript(text) {
    currentTranscript.value = text
  }
  
  function clearTranscript() {
    currentTranscript.value = ''
  }
  
  function clearMessages() {
    messages.value = []
  }
  
  return {
    messages,
    isLoading,
    isListening,
    currentTranscript,
    addMessage,
    setListening,
    setTranscript,
    clearTranscript,
    clearMessages
  }
})
