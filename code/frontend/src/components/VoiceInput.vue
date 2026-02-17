<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { useChatStore } from '../stores/chat'
import { useWaveform } from '../composables/useWaveform'
import { useVAD } from '../composables/useVAD'
import { useWakeWord } from '../composables/useWakeWord'
import ASRService from '../services/asr'

// 唤醒响应事件
const emit = defineEmits(['wake-response', 'recording-countdown'])

const chatStore = useChatStore()
const isSupported = ref(false)
const buttonText = ref('按住说话')
const useVADMode = ref(false) // 是否使用 VAD 自动模式
const useWakeWordMode = ref(false) // 是否使用唤醒词模式
const recordingCountdown = ref(0) // 录音倒计时
const countdownInterval = ref(null)

// 波形可视化
const waveformCanvas = ref(null)
const { init: initWaveform, startVisualization, stopVisualization } = useWaveform()

// VAD 语音活动检测 - 优化参数
const {
  isSpeechActive,
  currentVolume,
  start: startVAD,
  stop: stopVAD,
  onSpeechStart,
  onSpeechEnd
} = useVAD({
  threshold: 0.1,           // 0.02 太敏感，0.1 是更合理的默认值
  endSilenceDuration: 1000, // 800ms 太短，1000ms 减少截断
  minSpeechDuration: 300
})

// 唤醒词检测
const {
  wakeWordDetected,
  isListening: isWakeWordListening,
  isInitialized: isWakeWordInitialized,
  wakeResponseState,
  init: initWakeWord,
  start: startWakeWord,
  stop: stopWakeWord,
  onWakeWord: onWakeWordDetected,
  onWakeResponse,
  resetResponseState
} = useWakeWord()

// 检查浏览器是否支持语音识别
onMounted(async () => {
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
      if (useVADMode.value) {
        stopVAD()
      }
    }
  })

  // 注册 VAD 事件回调
  onSpeechStart(() => {
    console.log('VAD: Speech detected, starting recording')
    chatStore.setListening(true)
    chatStore.clearTranscript()
    buttonText.value = '正在说话...'
  })

  onSpeechEnd(() => {
    console.log('VAD: Speech ended, stopping recording')
    chatStore.setListening(false)
    buttonText.value = useWakeWordMode.value ? '唤醒词模式' : '按住说话'
    ASRService.stop()
  })

  // 初始化唤醒词检测
  try {
    const wakeWordPath = '/wake-word/hey_assistant_zh.ppn'
    // 0.5 是推荐默认值，0.6 稍高可能增加误检
    await initWakeWord(wakeWordPath, { sensitivity: 0.5 })
    console.log('Wake word detection initialized')
  } catch (err) {
    console.warn('Failed to initialize wake word detection:', err)
  }

  // 注册唤醒词检测回调
  onWakeWordDetected(() => {
    console.log('Wake word detected! Starting recording...')
    handleWakeWordDetected()
  })

  // 注册唤醒响应状态回调
  onWakeResponse((state) => {
    console.log('Wake response state:', state)
    emit('wake-response', state)
    
    // 根据状态更新 UI
    if (state === 'waking') {
      buttonText.value = '唤醒中...'
    } else if (state === 'recording') {
      buttonText.value = '正在说话...'
    } else if (state === 'processing') {
      buttonText.value = '处理中...'
    } else if (state === 'idle') {
      buttonText.value = useWakeWordMode.value ? '唤醒词模式' : '按住说话'
    }
  })
})

onUnmounted(() => {
  ASRService.stop()
  if (useVADMode.value) {
    stopVAD()
  }
  if (useWakeWordMode.value) {
    stopWakeWord()
  }
})

// 处理唤醒词检测事件
function handleWakeWordDetected() {
  if (!useWakeWordMode.value) return

  // 开始录音
  startWakeWordRecording()
}

// 开始唤醒词后的录音
async function startWakeWordRecording() {
  chatStore.setListening(true)
  chatStore.clearTranscript()
  buttonText.value = '正在说话...'

  // 初始化波形可视化
  await initVisualization()

  // 开始 ASR
  ASRService.start()

  // 启动倒计时
  const totalDuration = 5000
  recordingCountdown.value = totalDuration / 1000
  
  countdownInterval.value = setInterval(() => {
    recordingCountdown.value--
    emit('recording-countdown', recordingCountdown.value)
    
    if (recordingCountdown.value <= 0) {
      clearInterval(countdownInterval.value)
    }
  }, 1000)

  // 5秒后自动停止录音（模拟松开鼠标）
  setTimeout(() => {
    if (chatStore.isListening) {
      wakeWordStopRecording()
    }
  }, totalDuration)
}

// 停止录音（用于唤醒词模式）
function wakeWordStopRecording() {
  // 清除倒计时
  if (countdownInterval.value) {
    clearInterval(countdownInterval.value)
    countdownInterval.value = null
  }
  recordingCountdown.value = 0
  
  // 重置唤醒响应状态
  resetResponseState()
  
  // 调用手动停止录音
  manualStopRecording()
}

// 切换唤醒词模式
async function toggleWakeWordMode() {
  useWakeWordMode.value = !useWakeWordMode.value

  if (useWakeWordMode.value) {
    // 启用唤醒词模式
    buttonText.value = '唤醒词模式'
    try {
      await startWakeWord()
      console.log('Wake word mode enabled')
    } catch (error) {
      console.error('Failed to start wake word detection:', error)
      useWakeWordMode.value = false
      buttonText.value = '按住说话'
    }
  } else {
    // 禁用唤醒词模式
    stopWakeWord()
    chatStore.setListening(false)
    buttonText.value = '按住说话'
    console.log('Wake word mode disabled')
  }
}

// 获取媒体流并启动可视化
async function initVisualization() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    if (waveformCanvas.value) {
      initWaveform(waveformCanvas.value)
    }
    startVisualization(stream)
    return stream
  } catch (error) {
    console.warn('Could not access microphone for visualization:', error)
    return null
  }
}

// 鼠标按下开始录音 (手动模式)
async function startRecording() {
  if (!isSupported.value || useVADMode.value) return
  
  // 检查麦克风是否可用
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    alert('请使用 HTTPS 访问以使用语音功能，或检查浏览器权限')
    return
  }
  
  chatStore.setListening(true)
  chatStore.clearTranscript()
  buttonText.value = '监听中...'
  
  // 初始化波形可视化
  try {
    await initVisualization()
  } catch (error) {
    console.warn('Visualization init failed:', error)
  }
  
  // 使用阿里云 ASR
  ASRService.start()
}

// 鼠标松开停止录音 (手动模式)
function manualStopRecording() {
  chatStore.setListening(false)
  buttonText.value = useWakeWordMode.value ? '唤醒词模式' : '按住说话'

  // 停止波形可视化
  stopVisualization()

  ASRService.stop()
}

// 切换 VAD 模式
async function toggleVADMode() {
  useVADMode.value = !useVADMode.value
  
  if (useVADMode.value) {
    // 启用 VAD 自动模式
    buttonText.value = 'VAD模式'
    try {
      const stream = await initVisualization()
      await startVAD(stream)
      console.log('VAD mode enabled')
    } catch (error) {
      console.error('Failed to start VAD:', error)
      useVADMode.value = false
      buttonText.value = '按住说话'
    }
  } else {
    // 禁用 VAD 模式
    stopVAD()
    stopVisualization()
    chatStore.setListening(false)
    buttonText.value = '按住说话'
    console.log('VAD mode disabled')
  }
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
    <!-- 唤醒状态徽章 -->
    <Transition name="slide-down">
      <div 
        v-if="useWakeWordMode && wakeResponseState !== 'idle'" 
        class="wake-status-badge"
        :class="wakeResponseState"
      >
        <span class="status-icon">
          <template v-if="wakeResponseState === 'waking'">✨</template>
          <template v-else-if="wakeResponseState === 'recording'">🎤</template>
          <template v-else-if="wakeResponseState === 'processing'">💭</template>
        </span>
        <span class="status-text">
          <template v-if="wakeResponseState === 'waking'">唤醒中</template>
          <template v-else-if="wakeResponseState === 'recording'">
            录音中 
            <span v-if="recordingCountdown > 0" class="countdown">{{ recordingCountdown }}s</span>
          </template>
          <template v-else-if="wakeResponseState === 'processing'">处理中</template>
        </span>
        <!-- 脉冲光晕效果 -->
        <span class="pulse-ring"></span>
      </div>
    </Transition>

    <!-- 唤醒词检测成功提示 -->
    <Transition name="wake-pop">
      <div v-if="wakeWordDetected" class="wake-success-indicator">
        <span class="success-icon">✨</span>
        <span>唤醒成功！开始录音...</span>
      </div>
    </Transition>

    <div v-if="chatStore.isListening" class="waveform-container">
      <canvas ref="waveformCanvas" class="waveform-canvas"></canvas>
    </div>

    <div class="button-group">
      <button
        class="voice-button"
        :class="{ 
          listening: chatStore.isListening && !useVADMode && !useWakeWordMode, 
          'vad-mode': useVADMode,
          'wake-word-mode': useWakeWordMode,
          'waking': wakeResponseState === 'waking',
          'recording': wakeResponseState === 'recording'
        }"
        @mousedown="startRecording"
        @mouseup="manualStopRecording"
        @mouseleave="manualStopRecording"
        @touchstart.prevent="startRecording"
        @touchend.prevent="manualStopRecording"
        :disabled="useVADMode || useWakeWordMode"
      >
        <span class="icon">
          <template v-if="wakeResponseState === 'recording'">🔴</template>
          <template v-else-if="wakeResponseState === 'waking'">⚡</template>
          <template v-else-if="chatStore.isListening">🔴</template>
          <template v-else>🎤</template>
        </span>
        <span class="text">{{ buttonText }}</span>
      </button>

      <!-- VAD 模式切换按钮 -->
      <button
        class="mode-toggle vad-toggle"
        :class="{ active: useVADMode }"
        @click="toggleVADMode"
        title="切换 VAD 自动模式"
      >
        <span class="icon">{{ useVADMode ? '🤖' : '👆' }}</span>
      </button>

      <!-- 唤醒词模式切换按钮 -->
      <button
        class="mode-toggle wake-word-toggle"
        :class="{ active: useWakeWordMode }"
        @click="toggleWakeWordMode"
        :disabled="!isWakeWordInitialized"
        title="切换唤醒词模式"
      >
        <span class="icon">{{ useWakeWordMode ? '👂' : '💤' }}</span>
      </button>
    </div>

    <div v-if="useVADMode && isSpeechActive" class="vad-indicator">
      <span class="speaking-dot"></span>
      检测到语音
    </div>

    <div v-if="useWakeWordMode && isWakeWordListening && !wakeWordDetected" class="wake-indicator">
      <span class="listening-dot"></span>
      等待唤醒词 "嘿助手"
    </div>

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

.button-group {
  display: flex;
  align-items: center;
  gap: 12px;
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

.voice-button:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(102, 126, 234, 0.5);
}

.voice-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.voice-button.listening {
  background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
  box-shadow: 0 4px 15px rgba(245, 87, 108, 0.4);
  animation: pulse 1.5s infinite;
}

.voice-button.vad-mode {
  background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
  box-shadow: 0 4px 15px rgba(79, 172, 254, 0.4);
}

.voice-button.wake-word-mode {
  background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);
  box-shadow: 0 4px 15px rgba(250, 112, 154, 0.4);
}

.mode-toggle {
  width: 44px;
  height: 44px;
  border: 2px solid #667eea;
  border-radius: 50%;
  background: transparent;
  color: #667eea;
  font-size: 18px;
  cursor: pointer;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  justify-content: center;
}

.mode-toggle:hover {
  background: rgba(102, 126, 234, 0.1);
}

.mode-toggle.active {
  background: #667eea;
  color: white;
  border-color: #667eea;
  animation: glow 2s infinite;
}

.mode-toggle:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.wake-word-toggle.active {
  background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);
  border-color: #fa709a;
}

@keyframes pulse {
  0%, 100% {
    box-shadow: 0 4px 15px rgba(245, 87, 108, 0.4);
  }
  50% {
    box-shadow: 0 4px 25px rgba(245, 87, 108, 0.7);
  }
}

@keyframes glow {
  0%, 100% {
    box-shadow: 0 0 10px rgba(102, 126, 234, 0.4);
  }
  50% {
    box-shadow: 0 0 20px rgba(102, 126, 234, 0.7);
  }
}

.icon {
  font-size: 20px;
}

.vad-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background: rgba(79, 172, 254, 0.1);
  border: 1px solid rgba(79, 172, 254, 0.3);
  border-radius: 12px;
  color: #4facfe;
  font-size: 14px;
  animation: fadeIn 0.3s ease;
}

.wake-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background: rgba(250, 112, 154, 0.1);
  border: 1px solid rgba(250, 112, 154, 0.3);
  border-radius: 12px;
  color: #fa709a;
  font-size: 14px;
  animation: fadeIn 0.3s ease;
}

/* 唤醒状态徽章 */
.wake-status-badge {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 20px;
  border-radius: 20px;
  font-size: 14px;
  font-weight: 500;
  position: relative;
  overflow: hidden;
  z-index: 1;
}

.wake-status-badge.waking {
  background: linear-gradient(135deg, #a8edea 0%, #fed6e3 100%);
  color: #667eea;
  box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
}

.wake-status-badge.recording {
  background: linear-gradient(135deg, #ff9a9e 0%, #fecfef 100%);
  color: #f5576c;
  box-shadow: 0 4px 15px rgba(245, 87, 108, 0.3);
}

.wake-status-badge.processing {
  background: linear-gradient(135deg, #a18cd1 0%, #fbc2eb 100%);
  color: #764ba2;
  box-shadow: 0 4px 15px rgba(118, 75, 162, 0.3);
}

.wake-status-badge .status-icon {
  font-size: 18px;
}

.wake-status-badge .status-text {
  display: flex;
  align-items: center;
  gap: 6px;
}

.wake-status-badge .countdown {
  background: rgba(255, 255, 255, 0.3);
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 12px;
  font-weight: bold;
}

/* 脉冲光晕效果 */
.pulse-ring {
  position: absolute;
  top: 50%;
  left: 50%;
  width: 100%;
  height: 100%;
  border-radius: 50%;
  background: inherit;
  opacity: 0.4;
  transform: translate(-50%, -50%) scale(1);
  z-index: -1;
  animation: pulseRing 1.5s ease-out infinite;
}

@keyframes pulseRing {
  0% {
    transform: translate(-50%, -50%) scale(1);
    opacity: 0.4;
  }
  100% {
    transform: translate(-50%, -50%) scale(2.5);
    opacity: 0;
  }
}

/* 唤醒成功提示 */
.wake-success-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 14px 24px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 16px;
  color: white;
  font-size: 16px;
  font-weight: 600;
  box-shadow: 0 8px 25px rgba(102, 126, 234, 0.5);
  animation: wakeSuccess 0.6s cubic-bezier(0.68, -0.55, 0.265, 1.55);
}

.wake-success-indicator .success-icon {
  font-size: 24px;
  animation: bounce 0.6s ease;
}

@keyframes wakeSuccess {
  0% {
    opacity: 0;
    transform: scale(0.5) translateY(20px);
  }
  100% {
    opacity: 1;
    transform: scale(1) translateY(0);
  }
}

@keyframes bounce {
  0%, 100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-10px);
  }
}

/* 按钮唤醒中状态 */
.voice-button.waking {
  background: linear-gradient(135deg, #a8edea 0%, #fed6e3 100%) !important;
  color: #667eea !important;
  animation: shake 0.5s ease;
}

.voice-button.recording {
  background: linear-gradient(135deg, #ff9a9e 0%, #fecfef 100%) !important;
  color: #f5576c !important;
  box-shadow: 0 4px 25px rgba(245, 87, 108, 0.6) !important;
  animation: recordingPulse 1s infinite;
}

@keyframes shake {
  0%, 100% { transform: translateX(0); }
  25% { transform: translateX(-5px); }
  75% { transform: translateX(5px); }
}

@keyframes recordingPulse {
  0%, 100% {
    box-shadow: 0 4px 25px rgba(245, 87, 108, 0.6);
  }
  50% {
    box-shadow: 0 4px 35px rgba(245, 87, 108, 0.9);
  }
}

/* 过渡动画 - 滑入 */
.slide-down-enter-active,
.slide-down-leave-active {
  transition: all 0.4s cubic-bezier(0.68, -0.55, 0.265, 1.55);
}

.slide-down-enter-from,
.slide-down-leave-to {
  opacity: 0;
  transform: translateY(-20px);
}

/* 唤醒弹窗动画 */
.wake-pop-enter-active {
  animation: wakePopIn 0.5s ease;
}

.wake-pop-leave-active {
  animation: wakePopOut 0.3s ease;
}

@keyframes wakePopIn {
  0% {
    opacity: 0;
    transform: scale(0.3) rotate(-10deg);
  }
  50% {
    transform: scale(1.1) rotate(3deg);
  }
  100% {
    opacity: 1;
    transform: scale(1) rotate(0);
  }
}

@keyframes wakePopOut {
  0% {
    opacity: 1;
    transform: scale(1);
  }
  100% {
    opacity: 0;
    transform: scale(0.5);
  }
}

/* 过渡动画 */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.speaking-dot {
  width: 8px;
  height: 8px;
  background: #4facfe;
  border-radius: 50%;
  animation: speaking 0.5s infinite alternate;
}

.listening-dot {
  width: 8px;
  height: 8px;
  background: #fa709a;
  border-radius: 50%;
  animation: listeningPulse 1.5s infinite;
}

@keyframes speaking {
  from {
    opacity: 0.5;
    transform: scale(0.8);
  }
  to {
    opacity: 1;
    transform: scale(1.2);
  }
}

@keyframes listeningPulse {
  0%, 100% {
    opacity: 0.3;
    transform: scale(0.8);
    box-shadow: 0 0 0 0 rgba(250, 112, 154, 0.4);
  }
  50% {
    opacity: 1;
    transform: scale(1.2);
    box-shadow: 0 0 10px 5px rgba(250, 112, 154, 0.2);
  }
}

@keyframes wakePop {
  from {
    opacity: 0;
    transform: scale(0.8);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}

@keyframes wave {
  0% {
    transform: rotate(0deg);
  }
  25% {
    transform: rotate(-20deg);
  }
  50% {
    transform: rotate(20deg);
  }
  75% {
    transform: rotate(-10deg);
  }
  100% {
    transform: rotate(0deg);
  }
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
