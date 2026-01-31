<script setup>
import { ref, nextTick, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useChatStore } from '../stores/chat'
import { useAuthStore } from '../stores/auth'
import MessageBubble from '../components/MessageBubble.vue'
import VoiceInput from '../components/VoiceInput.vue'
import Live2DCharacter from '../components/Live2DCharacter.vue'
import BackendService from '../services/openclaw'
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

// 滚动到底部
async function scrollToBottom() {
  await nextTick()
  if (messageContainer.value) {
    messageContainer.value.scrollTop = messageContainer.value.scrollHeight
  }
}

// 发送消息
async function sendMessage(content = null) {
  const text = content || userInput.value.trim()
  if (!text) return

  // 验证是否已配置 API Key
  if (!authStore.isAuthenticated) {
    alert('请先在设置页面配置 API Key')
    router.push('/settings')
    return
  }

  // 添加用户消息
  chatStore.addMessage('user', text)
  userInput.value = ''
  chatStore.isLoading = true
  isSpeechInterrupted.value = false

  try {
    // 发送消息并获取回复
    const reply = await BackendService.sendMessage(text)
    
    chatStore.addMessage('assistant', reply)
    
    // 自动播放语音
    if (isAutoPlay.value) {
      // 触发 Live2D 说话动画
      if (showLive2D.value && live2dRef.value) {
        live2dRef.value.startSpeaking()
      }
      
      TTSService.speak(reply)
      
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
    chatStore.addMessage('assistant', `抱歉，发生了错误: ${error.message}`)
    console.error('Send message error:', error)
  } finally {
    chatStore.isLoading = false
    scrollToBottom()
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

  // 初始化 TTS
  TTSService.init({
    appKey: localStorage.getItem('aliyun_appkey') || '',
    token: localStorage.getItem('aliyun_token') || '',
    onEnd: () => console.log('TTS play ended'),
    onError: (error) => console.error('TTS error:', error),
    onSpeechInterrupt: () => {
      console.log('Speech interrupted by user')
    }
  })
})
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
      
      <VoiceInput />
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
