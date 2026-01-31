<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { useAudioAnalyzer } from '../composables/useAudioAnalyzer'

const props = defineProps({
  modelUrl: {
    type: String,
    default: '/models/live2d/koharu/koharu.model3.json'
  },
  autoPlay: {
    type: Boolean,
    default: true
  }
})

const emit = defineEmits(['loaded', 'error'])

const canvasRef = ref(null)
const isLoading = ref(true)
const model = ref(null)

// 音频分析器
const { analyzeAudio, getMouthOpenness } = useAudioAnalyzer()

// Live2D 模型实例
let live2DModel = null
let app = null

/**
 * 加载 Live2D 模型
 */
async function loadModel() {
  try {
    isLoading.value = true
    
    // 动态加载 Live2D Cubism SDK
    if (!window.Live2DCubismCore) {
      await loadScript('https://cubism.live2d.com/sdk/web/cubismubsdk.js')
    }
    
    // 使用 Live2D Viewer 简化加载
    await loadScript('https://cdn.jsdelivr.net/npm/live2d-viewer@1.1.1/dist/live2d-viewer.min.js')
    
    // 创建模型
    app = new window.Live2DViewer.App({
      canvas: canvasRef.value,
      model: props.modelUrl,
      background: 'transparent',
      debug: false
    })
    
    app.on('load', (model) => {
      live2DModel = model
      isLoading.value = false
      emit('loaded', model)
      startIdleAnimation()
    })
    
    app.on('error', (error) => {
      emit('error', error)
      isLoading.value = false
    })
    
  } catch (error) {
    console.error('Failed to load Live2D model:', error)
    isLoading.value = false
    emit('error', error)
  }
}

/**
 * 加载脚本
 */
function loadScript(src) {
  return new Promise((resolve, reject) => {
    const script = document.createElement('script')
    script.src = src
    script.onload = resolve
    script.onerror = reject
    document.head.appendChild(script)
  })
}

/**
 * 播放说话动画
 */
function speak(audioUrl) {
  if (!live2DModel) return
  
  const audio = new Audio(audioUrl)
  
  audio.onplay = () => {
    // 说话时：嘴巴开合 + 轻微晃动
    startTalkingAnimation()
    
    // 分析音频音量控制嘴巴
    analyzeAudio(audio, (mouthValue) => {
      setMouthOpen(mouthValue)
    })
  }
  
  audio.onended = () => {
    stopTalkingAnimation()
  }
  
  audio.play()
}

/**
 * 说话动画状态
 */
let talkingInterval = null
let idleInterval = null

function startTalkingAnimation() {
  // 停止空闲动画
  stopIdleAnimation()
  
  // 说话时添加轻微身体晃动
  talkingInterval = setInterval(() => {
    if (live2DModel && !isSpeaking.value) return
    
    const breathe = Math.sin(Date.now() / 500) * 0.02
    const tilt = Math.sin(Date.now() / 300) * 0.03
    
    live2DModel.setParameterValue('PARAM_BODY_ANGLE_X', tilt)
    live2DModel.setParameterValue('PARAM_BODY_ANGLE_Z', breathe)
  }, 50)
}

function stopTalkingAnimation() {
  if (talkingInterval) {
    clearInterval(talkingInterval)
    talkingInterval = null
  }
  
  // 恢复空闲动画
  startIdleAnimation()
}

/**
 * 设置嘴巴开合度
 */
function setMouthOpen(value) {
  if (!live2DModel) return
  
  // 映射音量到嘴巴开合 (0-1)
  const mouthOpen = Math.min(1, Math.max(0, value))
  
  // 使用 ParamMouthOpenY 控制嘴巴
  live2DModel.setParameterValue('ParamMouthOpenY', mouthOpen * 0.8)
  
  // 同时调整下巴角度
  live2DModel.setParameterValue('ParamJawOpen', mouthOpen * 0.5)
}

/**
 * 空闲动画（呼吸效果）
 */
function startIdleAnimation() {
  if (idleInterval) return
  
  idleInterval = setInterval(() => {
    if (!live2DModel || isSpeaking.value) return
    
    // 轻微呼吸效果
    const breathe = Math.sin(Date.now() / 2000) * 0.01
    
    live2DModel.setParameterValue('PARAM_BODY_ANGLE_Z', breathe)
    
    // 眼睛微动
    const eyeBlink = Math.sin(Date.now() / 3000) > 0.95
    if (eyeBlink) {
      live2DModel.setParameterValue('PARAM_EYE_L_OPEN', 0)
      live2DModel.setParameterValue('PARAM_EYE_R_OPEN', 0)
    } else {
      live2DModel.setParameterValue('PARAM_EYE_L_OPEN', 1)
      live2DModel.setParameterValue('PARAM_EYE_R_OPEN', 1)
    }
  }, 100)
}

function stopIdleAnimation() {
  if (idleInterval) {
    clearInterval(idleInterval)
    idleInterval = null
  }
}

/**
 * 随机动作（增加生动感）
 */
function randomMotion() {
  if (!live2DModel || isSpeaking.value) return
  
  const motions = [
    { param: 'PARAM_ARM_L_L', value: 0.1, duration: 500 },
    { param: 'PARAM_ARM_R_L', value: 0.1, duration: 500 },
    { param: 'PARAM_ANGLE_X', value: 0.1, duration: 300 },
    { param: 'PARAM_BODY_ANGLE_X', value: 0.05, duration: 400 }
  ]
  
  const motion = motions[Math.floor(Math.random() * motions.length)]
  
  if (live2DModel) {
    const currentValue = live2DModel.getParameterValue(motion.param) || 0
    live2DModel.setParameterValue(motion.param, currentValue + motion.value)
    
    setTimeout(() => {
      if (live2DModel) {
        live2DModel.setParameterValue(motion.param, currentValue)
      }
    }, motion.duration)
  }
}

// 状态
const isSpeaking = ref(false)

/**
 * 开始说话（外部调用）
 */
function startSpeaking() {
  isSpeaking.value = true
  startTalkingAnimation()
}

/**
 * 停止说话（外部调用）
 */
function stopSpeaking() {
  isSpeaking.value = false
  stopTalkingAnimation()
  setMouthOpen(0)
}

// 暴露方法给父组件
defineExpose({
  speak,
  startSpeaking,
  stopSpeaking,
  loadModel
})

onMounted(() => {
  if (props.autoPlay) {
    loadModel()
  }
  
  // 随机触发小动作
  setInterval(randomMotion, 5000)
})

onUnmounted(() => {
  stopTalkingAnimation()
  stopIdleAnimation()
  
  if (app) {
    app.dispose()
  }
})
</script>

<template>
  <div class="live2d-container">
    <!-- 加载状态 -->
    <div v-if="isLoading" class="loading-overlay">
      <div class="loading-spinner"></div>
      <p>加载 Live2D 模型中...</p>
    </div>
    
    <!-- Live2D Canvas -->
    <canvas 
      ref="canvasRef" 
      class="live2d-canvas"
      width="400"
      height="500"
    ></canvas>
    
    <!-- 控制按钮 -->
    <div class="live2d-controls">
      <button @click="startSpeaking" :disabled="!model">开始说话</button>
      <button @click="stopSpeaking" :disabled="!model">停止说话</button>
    </div>
  </div>
</template>

<style scoped>
.live2d-container {
  position: relative;
  width: 400px;
  height: 500px;
  background: linear-gradient(180deg, #f5f5f5 0%, #e8e8e8 100%);
  border-radius: 20px;
  overflow: hidden;
  box-shadow: 0 10px 40px rgba(0,0,0,0.1);
}

.live2d-canvas {
  width: 100%;
  height: 100%;
  display: block;
}

.loading-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: rgba(255,255,255,0.9);
  z-index: 10;
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 3px solid #f0f0f0;
  border-top-color: #667eea;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.loading-overlay p {
  margin-top: 16px;
  color: #666;
  font-size: 14px;
}

.live2d-controls {
  position: absolute;
  bottom: 16px;
  left: 0;
  right: 0;
  display: flex;
  justify-content: center;
  gap: 12px;
}

.live2d-controls button {
  padding: 8px 20px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 20px;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.3s;
}

.live2d-controls button:hover:not(:disabled) {
  transform: scale(1.05);
  box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
}

.live2d-controls button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
