<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useChatStore } from '../stores/chat'
import { useWaveform } from '../composables/useWaveform'
import ASRService from '../services/asr'

const chatStore = useChatStore()
const isSupported = ref(false)
const buttonText = ref('按住说话')

// 波形可视化
const waveformCanvas = ref(null)
const { init: initWaveform, startVisualization, stopVisualization } = useWaveform()

// 检查浏览器是否支持语音识别
onMounted(() => {
  if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
    isSupported.value = true
  } else {
    console.warn('Speech recognition not supported')
  }

  // 初始化 ASR 服务
  ASRService.init({
    appKey: localStorage.getItem('aliyun_appkey') || '',
    onTranscript: (text, isFinal = false) => {
      chatStore.setTranscript(text, isFinal)
    },
    onError: (error) => {
      console.error('ASR Error:', error)
      chatStore.setListening(false)
    }
  })
})

onUnmounted(() => {
  ASRService.stop()
})

// 鼠标按下开始录音
async function startRecording() {
  if (!isSupported.value) return
  
  chatStore.setListening(true)
  chatStore.clearTranscript()
  buttonText.value = '监听中...'
  
  // 初始化波形可视化
  if (waveformCanvas.value) {
    initWaveform(waveformCanvas.value)
  }
  
  // 获取媒体流并启动可视化
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    startVisualization(stream)
  } catch (error) {
    console.warn('Could not access microphone for visualization:', error)
  }
  
  // 使用阿里云 ASR
  ASRService.start()
}

// 鼠标松开停止录音
function stopRecording() {
  chatStore.setListening(false)
  buttonText.value = '按住说话'
  
  // 停止波形可视化
  stopVisualization()
  
  ASRService.stop()
}

// 处理点击（发送当前转写内容）
function handleClick() {
  if (chatStore.currentTranscript.trim()) {
    // 发送消息逻辑
  }
}
</script>

<template>
  <div class="voice-input">
    <div v-if="chatStore.isListening" class="waveform-container">
      <canvas ref="waveformCanvas" class="waveform-canvas"></canvas>
    </div>
    
    <button
      class="voice-button"
      :class="{ listening: chatStore.isListening }"
      @mousedown="startRecording"
      @mouseup="stopRecording"
      @mouseleave="stopRecording"
      @touchstart.prevent="startRecording"
      @touchend.prevent="stopRecording"
    >
      <span class="icon">{{ chatStore.isListening ? '🔴' : '🎤' }}</span>
      <span class="text">{{ buttonText }}</span>
    </button>
    
    <div v-if="chatStore.currentTranscript" class="transcript" :class="{ 'is-final': chatStore.isFinalTranscript }">
      <span v-if="!chatStore.isFinalTranscript" class="listening-indicator">•••</span>
      <span v-else class="final-indicator">✓</span>
      {{ chatStore.currentTranscript }}
    </div>
  </div>
</template>

<style scoped>
.voice-input {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.waveform-container {
  width: 100%;
  max-width: 300px;
  height: 60px;
  background: rgba(102, 126, 234, 0.1);
  border-radius: 8px;
  overflow: hidden;
  margin-bottom: 8px;
}

.waveform-canvas {
  width: 100%;
  height: 100%;
}

.voice-button {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 24px;
  border: none;
  border-radius: 24px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  font-size: 16px;
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
}

.voice-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(102, 126, 234, 0.5);
}

.voice-button.listening {
  background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
  box-shadow: 0 4px 15px rgba(245, 87, 108, 0.4);
  animation: pulse 1.5s infinite;
}

@keyframes pulse {
  0%, 100% {
    box-shadow: 0 4px 15px rgba(245, 87, 108, 0.4);
  }
  50% {
    box-shadow: 0 4px 25px rgba(245, 87, 108, 0.7);
  }
}

.icon {
  font-size: 20px;
}

.transcript {
  max-width: 80%;
  padding: 8px 16px;
  background: rgba(102, 126, 234, 0.1);
  border-radius: 12px;
  font-size: 14px;
  color: #666;
  text-align: center;
  display: flex;
  align-items: center;
  gap: 6px;
  animation: fadeIn 0.3s ease;
}

.transcript.is-final {
  background: rgba(76, 175, 80, 0.1);
  color: #4CAF50;
  border: 1px solid rgba(76, 175, 80, 0.3);
}

.listening-indicator {
  color: #f5576c;
  font-weight: bold;
  animation: blink 1s infinite;
}

.final-indicator {
  color: #4CAF50;
  font-weight: bold;
}

@keyframes blink {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.3;
  }
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(-5px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>
