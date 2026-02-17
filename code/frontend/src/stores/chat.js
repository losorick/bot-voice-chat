import { defineStore } from 'pinia'
import { ref } from 'vue'

const STORAGE_KEY = 'chat_messages'

export const useChatStore = defineStore('chat', () => {
  const messages = ref([])
  const isLoading = ref(false)
  const isListening = ref(false)
  const currentTranscript = ref('')
  const intermediateTranscript = ref('')
  const isFinalTranscript = ref(false)

  // 从本地存储加载消息
  function loadFromStorage() {
    try {
      const stored = localStorage.getItem(STORAGE_KEY)
      if (stored) {
        messages.value = JSON.parse(stored)
      }
    } catch (e) {
      console.error('Failed to load messages from storage:', e)
    }
  }

  // 保存消息到本地存储
  function saveToStorage() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(messages.value))
    } catch (e) {
      console.error('Failed to save messages to storage:', e)
    }
  }

  // 初始化时加载
  loadFromStorage()
  
  function addMessage(role, content) {
    messages.value.push({
      role,
      content,
      timestamp: Date.now()
    })
    saveToStorage()
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
    saveToStorage()
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
