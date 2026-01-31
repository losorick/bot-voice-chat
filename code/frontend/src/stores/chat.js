import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useChatStore = defineStore('chat', () => {
  const messages = ref([])
  const isLoading = ref(false)
  const isListening = ref(false)
  const currentTranscript = ref('')
  const intermediateTranscript = ref('')
  const isFinalTranscript = ref(false)
  
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
  
  function setTranscript(text, isFinal = false) {
    if (isFinal) {
      // 最终结果
      currentTranscript.value = text
      intermediateTranscript.value = ''
      isFinalTranscript.value = true
    } else {
      // 中间结果 - 实时更新
      intermediateTranscript.value = text
      currentTranscript.value = text
      isFinalTranscript.value = false
    }
  }
  
  function clearTranscript() {
    currentTranscript.value = ''
    intermediateTranscript.value = ''
    isFinalTranscript.value = false
  }
  
  function clearMessages() {
    messages.value = []
  }
  
  return {
    messages,
    isLoading,
    isListening,
    currentTranscript,
    intermediateTranscript,
    isFinalTranscript,
    addMessage,
    setListening,
    setTranscript,
    clearTranscript,
    clearMessages
  }
})
