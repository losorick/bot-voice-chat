<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { useAudioAnalyzer } from '../composables/useAudioAnalyzer'

const props = defineProps({
  modelUrl: {
    type: String,
    default: '/models/live2d/haru/haru_greeter_t03.model3.json'
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
const isSpeaking = ref(false)

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
    
    // 动态加载 Live2D Cubism Core (本地或 CDN)
    if (!window.Live2DCubismCore) {
      // 优先尝试本地加载
      const localLoaded = await loadScriptSafe('/live2d.min.js')
      if (!localLoaded) {
        // 回退到 CDN
        await loadScript('https://cdn.jsdelivr.net/gh/dylanNew/live2d/webgl/Live2D/lib/live2d.min.js')
      }
    }
    
    // 动态加载 pixi-live2d-display (CDN)
    if (!window.PIXI?.live2d) {
      await loadScript('https://cdn.jsdelivr.net/npm/pixi-live2d-display@0.4.0/dist/index.min.js')
    }
    
    // 创建 PIXI 应用
    const PIXI = window.PIXI
    app = new PIXI.Application({
      view: canvasRef.value,
      width: 400,
      height: 500,
      backgroundAlpha: 0,
      resolution: window.devicePixelRatio || 1,
      autoDensity: true
    })
    
    // 加载 Live2D 模型
    const { Live2DModel } = window.PIXI.live2d
    
    // 获取完整的模型 URL
    const fullModelUrl = props.modelUrl.startsWith('/') 
      ? props.modelUrl 
      : `/${props.modelUrl}`
    
    live2DModel = await Live2DModel.from(fullModelUrl)
    
    // 设置模型位置和大小
    live2DModel.position.set(200, 280)
    live2DModel.scale.set(0.35, 0.35)
    live2DModel.anchor.set(0.5, 0.5)
    
    app.stage.addChild(live2DModel)
    
    // 注册 Ticker 用于自动更新
    Live2DModel.registerTicker(PIXI.Ticker)
    
    isLoading.value = false
    model.value = live2DModel
    emit('loaded', live2DModel)
    
    // 启动空闲动画
    startIdleAnimation()
    
  } catch (error) {
    console.error('Failed to load Live2D model:', error)
    isLoading.value = false
    emit('error', error)
  }
}

/**
 * 加载脚本（安全版本，返回是否成功）
 */
function loadScriptSafe(src) {
  return new Promise((resolve) => {
    const script = document.createElement('script')
    script.src = src
    script.onload = () => resolve(true)
    script.onerror = () => resolve(false)
    document.head.appendChild(script)
  })
}

/**
 * 加载脚本（失败抛错）
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
 * 设置嘴巴开合度
 */
function setMouthOpen(value) {
  if (!live2DModel) return
  
  // 映射音量到嘴巴开合 (0-1)
  const mouthOpen = Math.min(1, Math.max(0, value))
  
  try {
    live2DModel.setParameterValue('PARAM_MOUTH_OPEN_Y', mouthOpen * 1.5)
  } catch (e) {
    // 如果模型不支持，忽略
  }
}

/**
 * 说话动画状态
 */
let talkingInterval = null
let idleInterval = null

function startTalkingAnimation() {
  if (!live2DModel) return
  
  // 停止空闲动画
  stopIdleAnimation()
  
  // 说话时添加轻微身体晃动
  talkingInterval = setInterval(() => {
    if (live2DModel && !isSpeaking.value) return
    
    const breathe = Math.sin(Date.now() / 500) * 0.02
    const tilt = Math.sin(Date.now() / 300) * 0.03
    
    try {
      live2DModel.setParameterValue('PARAM_BODY_ANGLE_X', tilt)
      live2DModel.setParameterValue('PARAM_BODY_ANGLE_Z', breathe)
    } catch (e) {
      // 忽略
    }
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
 * 空闲动画（呼吸效果）
 */
function startIdleAnimation() {
  if (!live2DModel || idleInterval) return
  
  idleInterval = setInterval(() => {
    if (!live2DModel || isSpeaking.value) return
    
    // 轻微呼吸效果
    const breathe = Math.sin(Date.now() / 2000) * 0.01
    
    try {
      live2DModel.setParameterValue('PARAM_BODY_ANGLE_Z', breathe)
      
      // 眼睛微动 - 随机眨眼
      if (Math.random() < 0.002) {
        live2DModel.setParameterValue('PARAM_EYE_L_OPEN', 0)
        live2DModel.setParameterValue('PARAM_EYE_R_OPEN', 0)
        setTimeout(() => {
          if (live2DModel) {
            live2DModel.setParameterValue('PARAM_EYE_L_OPEN', 1)
            live2DModel.setParameterValue('PARAM_EYE_R_OPEN', 1)
          }
        }, 150)
      }
    } catch (e) {
      // 忽略
    }
  }, 50)
}

function stopIdleAnimation() {
  if (idleInterval) {
    clearInterval(idleInterval)
    idleInterval = null
  }
}

/**
 * 随机动作
 */
function randomMotion() {
  if (!live2DModel || isSpeaking.value) return
  
  try {
    const motions = [
      { param: 'PARAM_ANGLE_X', value: 0.05 },
      { param: 'PARAM_BODY_ANGLE_X', value: 0.03 },
      { param: 'PARAM_ARM_L_L', value: 0.05 },
      { param: 'PARAM_ARM_R_L', value: 0.05 }
    ]
    
    const motion = motions[Math.floor(Math.random() * motions.length)]
    const currentValue = live2DModel.getParameterValue(motion.param) || 0
    live2DModel.setParameterValue(motion.param, currentValue + motion.value)
    
    setTimeout(() => {
      if (live2DModel) {
        live2DModel.setParameterValue(motion.param, currentValue)
      }
    }, 300)
  } catch (e) {
    // 忽略
  }
}

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

/**
 * 播放说话动画
 */
function speak(audioUrl) {
  if (!live2DModel) return
  
  const audio = new Audio(audioUrl)
  
  audio.onplay = () => {
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

// 暴露方法给父组件
defineExpose({
  speak,
  startSpeaking,
  stopSpeaking,
  loadModel,
  get speaking() { return isSpeaking.value }
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
    app.destroy(true)
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
