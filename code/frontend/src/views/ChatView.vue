<script setup>
import { ref, nextTick, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useChatStore } from '../stores/chat'
import { useAuthStore } from '../stores/auth'
import MessageBubble from '../components/MessageBubble.vue'
import VoiceInput from '../components/VoiceInput.vue'
import Live2DCharacter from '../components/Live2DCharacter.vue'
import OpenClawService from '../services/openclaw-chat'
import TTSService from '../services/tts'

const router = useRouter()
const chatStore = useChatStore()
const authStore = useAuthStore()

const messageContainer = ref(null)
const userInput = ref('')
const isAutoPlay = ref(true)
const live2dRef = ref(null)
const showLive2D = ref(true)
const isSpeechInterrupted = ref(false)
const waitAudio = ref(null) // 等待语音 Audio 对象
const waitTimer = ref(null) // 超时定时器 ID
const isPlayingWaitAudio = ref(false)

// 滚动到底部
async function scrollToBottom() {
  await nextTick()
  if (messageContainer.value) {
    messageContainer.value.scrollTop = messageContainer.value.scrollHeight
  }
}

// 播放等待语音（支持不同类型）
async function playWaitAudio(type = 'waiting') {
  try {
    // 停止之前的等待语音
    stopWaitAudio()
    
    // 获取随机等待语音
    const response = await fetch(`${OpenClawService.baseUrl}/api/v1/wait-audio/random?type=${type}`)
    const result = await response.json()
    
    if (result.code === 200 && result.data) {
      // 确保 audioUrl 是完整路径
      const audioUrl = result.data.audioUrl.startsWith('http') || result.data.audioUrl.startsWith('/api') 
        ? result.data.audioUrl 
        : `${OpenClawService.baseUrl}${result.data.audioUrl}`
      console.log(`Playing wait audio [${type}]:`, result.data.text)
      
      waitAudio.value = new Audio(audioUrl)
      waitAudio.value.onended = () => {
        isPlayingWaitAudio.value = false
      }
      waitAudio.value.onerror = () => {
        console.warn('Wait audio play failed, skipping')
        isPlayingWaitAudio.value = false
      }
      
      waitAudio.value.play()
      isPlayingWaitAudio.value = true
    }
  } catch (error) {
    console.warn('Failed to play wait audio:', error)
  }
}

// 停止等待语音
function stopWaitAudio() {
  if (waitAudio.value) {
    waitAudio.value.pause()
    waitAudio.value.currentTime = 0
    waitAudio.value = null
  }
  isPlayingWaitAudio.value = false
}

// 取消超时定时器
function clearWaitTimer() {
  if (waitTimer.value) {
    clearTimeout(waitTimer.value)
    waitTimer.value = null
  }
}

// 设置等待超时定时器（1分钟 + 随机30-60秒，即90-120秒后播放 waiting 语音）
function scheduleWaitingAudio() {
  clearWaitTimer()
  
  // 基础延迟 1 分钟 + 随机 30-60 秒 = 90-120 秒
  const baseDelay = 60 * 1000 // 1 分钟
  const randomDelay = Math.floor(Math.random() * 30 + 30) * 1000 // 30-60 秒
  const totalDelay = baseDelay + randomDelay
  
  console.log(`Waiting audio will play in ${totalDelay / 1000} seconds`)
  
  waitTimer.value = setTimeout(() => {
    playWaitAudio('waiting')
    waitTimer.value = null
  }, totalDelay)
}

// 发送消息
async function sendMessage(content = null) {
  const text = content || userInput.value.trim()
  if (!text) return

  // 添加用户消息
  chatStore.addMessage('user', text)
  if (!content) userInput.value = ''
  chatStore.isLoading = true
  isSpeechInterrupted.value = false

  // ① 发送后立即播放确认类语音
  playWaitAudio('confirm')
  
  // 设置超时定时器（90-120秒后播放 waiting 语音）
  scheduleWaitingAudio()

  try {
    // 通过 OpenClaw 会话获取回复（包含 TTS 音频）
    const result = await OpenClawService.chat(text)
    
    // 停止等待语音和定时器
    stopWaitAudio()
    clearWaitTimer()
    
    // ③ 收到 AI 文本回复后、调用 subagent 总结前播放完成类语音
    playWaitAudio('completed')
    
    // 短暂延迟后继续（让 completed 语音播放完毕）
    await new Promise(resolve => setTimeout(resolve, 1000))
    
    // 添加 AI 回复
    chatStore.addMessage('assistant', result.reply)
    
    // 自动播放语音（使用总结后的内容）
    if (isAutoPlay.value) {
      // 触发 Live2D 说话动画
      if (showLive2D.value && live2dRef.value) {
        live2dRef.value.startSpeaking()
      }
      
      if (result.ttsAudio) {
        // 使用后端返回的 TTS 音频（总结后的内容）
        console.log('Playing summarized TTS audio')
        playTTSAudio(result.ttsAudio)
      } else if (result.ttsSummary) {
        // 使用总结文本调用 TTS
        TTSService.speak(result.ttsSummary)
      } else {
        // 回退到原始回复
        TTSService.speak(result.reply)
      }
      
      // TTS 播放结束时停止动画
      TTSService.onEnd = () => {
        if (live2dRef.value) {
          live2dRef.value.stopSpeaking()
        }
      }

      // 设置语音打断回调
      TTSService.onSpeechInterrupt = () => {
        isSpeechInterrupted.value = true
        if (live2dRef.value) {
          live2dRef.value.stopSpeaking()
        }
      }
    }

  } catch (error) {
    // 发生错误时也要停止等待语音和定时器
    stopWaitAudio()
    clearWaitTimer()
    chatStore.addMessage('assistant', `抱歉，发生了错误: ${error.message}`)
    console.error('Send message error:', error)
  } finally {
    chatStore.isLoading = false
    scrollToBottom()
  }
}

/**
 * 播放 Base64 编码的 TTS 音频
 */
function playTTSAudio(base64Audio) {
  try {
    // 移除 data:audio/wav;base64, 前缀
    const audioData = base64Audio.includes(',') 
      ? base64Audio.split(',')[1] 
      : base64Audio
    
    const binaryString = atob(audioData)
    const len = binaryString.length
    const bytes = new Uint8Array(len)
    for (let i = 0; i < len; i++) {
      bytes[i] = binaryString.charCodeAt(i)
    }
    
    const blob = new Blob([bytes], { type: 'audio/wav' })
    const url = URL.createObjectURL(blob)
    
    const audio = new Audio(url)
    audio.onended = () => {
      if (live2dRef.value) {
        live2dRef.value.stopSpeaking()
      }
      URL.revokeObjectURL(url)
    }
    audio.onerror = (error) => {
      console.error('TTS audio play error:', error)
      // 回退到原始 TTS
      if (TTSService) {
        TTSService.speak('播放音频失败')
      }
    }
    
    audio.play()
  } catch (error) {
    console.error('Failed to play TTS audio:', error)
  }
}

// 监听语音输入
watch(() => chatStore.currentTranscript, (newTranscript) => {
  if (newTranscript && !chatStore.isListening) {
    // 监听结束时自动发送
    sendMessage(newTranscript)
    chatStore.clearTranscript()
  }
})

// 处理键盘输入
function handleKeydown(event) {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    sendMessage()
  }
}

// 切换自动播放
function toggleAutoPlay() {
  isAutoPlay.value = !isAutoPlay.value
}

onMounted(() => {
  scrollToBottom()

  // 初始化 TTS (使用 DashScope cosyvoice-v3-flash)
  TTSService.init({
    voice: 'longhuhu_v3',  // 音色: longhuhu_v3
    onEnd: () => console.log('TTS play ended'),
    onError: (error) => console.error('TTS error:', error),
    onSpeechInterrupt: () => {
      console.log('Speech interrupted by user')
    }
  })
})

/**
 * 处理唤醒词检测响应状态
 * @param {string} state - 状态: 'waking' | 'recording' | 'processing' | 'idle'
 */
function handleWakeResponse(state) {
  console.log('Wake response state:', state)
  
  if (state === 'waking') {
    // 唤醒中 - 触发 Live2D 唤醒动画
    if (showLive2D.value && live2dRef.value) {
      live2dRef.value.triggerWakeResponse()
    }
    
    // 播放唤醒确认音效（可选）
    playWakeSound()
  } else if (state === 'recording') {
    // 录音中 - Live2D 进入倾听状态
    if (showLive2D.value && live2dRef.value) {
      // 可以让模型保持轻微的动画
    }
  } else if (state === 'processing') {
    // 处理中 - 停止 Live2D 录音状态
  } else if (state === 'idle') {
    // 恢复空闲状态
  }
}

/**
 * 播放唤醒确认音效
 */
function playWakeSound() {
  try {
    // 创建简单的提示音
    const audioContext = new (window.AudioContext || window.webkitAudioContext)()
    const oscillator = audioContext.createOscillator()
    const gainNode = audioContext.createGain()
    
    oscillator.connect(gainNode)
    gainNode.connect(audioContext.destination)
    
    // 设置音调 - 两个短音表示确认
    oscillator.frequency.setValueAtTime(800, audioContext.currentTime)
    oscillator.frequency.setValueAtTime(1000, audioContext.currentTime + 0.1)
    
    gainNode.gain.setValueAtTime(0.1, audioContext.currentTime)
    gainNode.gain.exponentialRampToValueAtTime(0.001, audioContext.currentTime + 0.2)
    
    oscillator.start(audioContext.currentTime)
    oscillator.stop(audioContext.currentTime + 0.2)
  } catch (error) {
    console.warn('Failed to play wake sound:', error)
  }
}
</script>

<template>
  <div class="chat-view">
    <header class="chat-header">
      <h1>🤖 Bot 语音助手</h1>
      <div class="header-actions">
        <label class="auto-play">
          <input 
            type="checkbox" 
            :checked="isAutoPlay" 
            @change="toggleAutoPlay"
          />
          🔊 自动播放
        </label>
        <label class="live2d-toggle">
          <input 
            type="checkbox" 
            :checked="showLive2D" 
            @change="showLive2D = !showLive2D"
          />
          🎨 Live2D
        </label>
        <router-link to="/settings" class="settings-btn">
          ⚙️ 设置
        </router-link>
      </div>
    </header>

    <main class="chat-container" ref="messageContainer">
      <!-- Live2D 虚拟形象 -->
      <div v-if="showLive2D" class="live2d-wrapper">
        <Live2DCharacter ref="live2dRef" />
      </div>
      <div v-if="chatStore.messages.length === 0" class="welcome">
        <div class="welcome-icon">👋</div>
        <h2>你好！我是 Bot 语音助手</h2>
        <p>我可以与你对话，按住下方按钮开始语音交流</p>
      </div>

      <div v-else class="messages">
        <MessageBubble
          v-for="(msg, index) in chatStore.messages"
          :key="index"
          :role="msg.role"
          :content="msg.content"
          :timestamp="msg.timestamp"
        />
      </div>

      <div v-if="chatStore.isLoading" class="loading">
        <span class="dot"></span>
        <span class="dot"></span>
        <span class="dot"></span>
      </div>

      <!-- 语音打断提示 -->
      <Transition name="fade">
        <div v-if="isSpeechInterrupted" class="interrupt-toast">
          🛑 语音已中断，请继续说话
        </div>
      </Transition>
    </main>

    <footer class="chat-footer">
      <div class="input-area">
        <textarea
          v-model="userInput"
          @keydown="handleKeydown"
          placeholder="输入消息..."
          rows="1"
        ></textarea>
        <button 
          class="send-button"
          @click="sendMessage()"
          :disabled="!userInput.trim() || chatStore.isLoading"
        >
          发送
        </button>
      </div>
      
      <!-- 语音输入组件，监听唤醒响应事件 -->
      <VoiceInput 
        @wake-response="handleWakeResponse"
      />
    </footer>
  </div>
</template>

<style scoped>
.chat-view {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: #f5f5f5;
}

.chat-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
  background: white;
  border-bottom: 1px solid #e0e0e0;
}

.chat-header h1 {
  font-size: 20px;
  margin: 0;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.header-actions {
  display: flex;
  gap: 16px;
  align-items: center;
}

.auto-play {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 14px;
  cursor: pointer;
}

.live2d-toggle {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 14px;
  cursor: pointer;
}

.settings-btn {
  padding: 8px 12px;
  background: #f0f0f0;
  border-radius: 8px;
  text-decoration: none;
  color: #333;
  font-size: 14px;
  transition: background 0.2s;
}

.settings-btn:hover {
  background: #e0e0e0;
}

.chat-container {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.live2d-wrapper {
  position: sticky;
  top: 0;
  z-index: 100;
  display: flex;
  justify-content: center;
  padding: 8px;
  background: linear-gradient(180deg, rgba(255,255,255,0.9) 0%, rgba(255,255,255,0) 100%);
}

.welcome {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  text-align: center;
  color: #666;
}

.welcome-icon {
  font-size: 64px;
  margin-bottom: 16px;
}

.welcome h2 {
  margin: 0 0 8px;
  font-size: 24px;
  color: #333;
}

.messages {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.loading {
  display: flex;
  justify-content: center;
  gap: 4px;
  padding: 16px;
}

.dot {
  width: 8px;
  height: 8px;
  background: #667eea;
  border-radius: 50%;
  animation: bounce 1.4s infinite ease-in-out both;
}

.dot:nth-child(1) { animation-delay: -0.32s; }
.dot:nth-child(2) { animation-delay: -0.16s; }

@keyframes bounce {
  0%, 80%, 100% { transform: scale(0); }
  40% { transform: scale(1); }
}

/* 语音打断提示样式 */
.interrupt-toast {
  position: fixed;
  bottom: 100px;
  left: 50%;
  transform: translateX(-50%);
  background: rgba(255, 82, 82, 0.9);
  color: white;
  padding: 12px 24px;
  border-radius: 24px;
  font-size: 14px;
  z-index: 1000;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.chat-footer {
  padding: 16px;
  background: white;
  border-top: 1px solid #e0e0e0;
}

.input-area {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}

.input-area textarea {
  flex: 1;
  padding: 12px;
  border: 1px solid #e0e0e0;
  border-radius: 12px;
  resize: none;
  font-size: 16px;
  line-height: 1.5;
  outline: none;
  transition: border-color 0.2s;
}

.input-area textarea:focus {
  border-color: #667eea;
}

.send-button {
  padding: 12px 24px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 12px;
  font-size: 16px;
  cursor: pointer;
  transition: opacity 0.2s;
}

.send-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
