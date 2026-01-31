/**
 * 语音录制 Composable
 */

import { ref, onUnmounted } from 'vue'

export function useVoiceRecord() {
  const isRecording = ref(false)
  const mediaRecorder = ref(null)
  const audioChunks = ref([])

  async function startRecord() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      
      mediaRecorder.value = new MediaRecorder(stream, {
        mimeType: 'audio/webm'
      })

      audioChunks.value = []

      mediaRecorder.value.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunks.value.push(event.data)
        }
      }

      mediaRecorder.value.start(3000)
      isRecording.value = true

    } catch (error) {
      console.error('Failed to start recording:', error)
      throw error
    }
  }

  function stopRecord() {
    return new Promise((resolve) => {
      if (!mediaRecorder.value) {
        resolve(null)
        return
      }

      mediaRecorder.value.onstop = () => {
        const audioBlob = new Blob(audioChunks.value, { type: 'audio/webm' })
        
        // 停止所有音轨
        mediaRecorder.value.stream.getTracks().forEach(track => track.stop())
        
        isRecording.value = false
        resolve(audioBlob)
      }

      mediaRecorder.value.stop()
    })
  }

  onUnmounted(() => {
    if (mediaRecorder.value && isRecording.value) {
      mediaRecorder.value.stop()
    }
  })

  return {
    isRecording,
    startRecord,
    stopRecord
  }
}
