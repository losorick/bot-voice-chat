/**
 * 语音活动检测 (VAD) - Voice Activity Detection
 * 使用 Web Audio API 检测语音开始和结束
 */

import { ref, onUnmounted } from 'vue'

export function useVAD(options = {}) {
  // 默认配置
  const config = {
    // 灵敏度阈值 (0-1)，值越低越灵敏
    threshold: options.threshold || 0.02,
    // 语音结束静音时间 (毫秒)
    endSilenceDuration: options.endSilenceDuration || 800,
    // 最小语音时长 (毫秒)
    minSpeechDuration: options.minSpeechDuration || 300,
    // 采样缓冲区大小
    bufferSize: options.bufferSize || 4096,
    // 平滑系数 (0-1)，用于减少抖动
    smoothingFactor: options.smoothingFactor || 0.8
  }

  // 状态
  const isListening = ref(false)
  const isSpeechActive = ref(false)
  const currentVolume = ref(0)

  // 内部变量
  let audioContext = null
  let analyser = null
  let microphone = null
  let dataArray = null
  let animationId = null
  let silenceStartTime = null
  let speechStartTime = null

  // 事件回调
  const onSpeechStartCallbacks = []
  const onSpeechEndCallbacks = []
  const onVolumeUpdateCallbacks = []

  /**
   * 初始化 AudioContext 和 Analyser
   */
  function initContext() {
    if (!audioContext) {
      audioContext = new (window.AudioContext || window.webkitAudioContext)()
    }
    
    if (!analyser) {
      analyser = audioContext.createAnalyser()
      analyser.fftSize = config.bufferSize
      analyser.smoothingTimeConstant = config.smoothingFactor
      analyser.minDecibels = -90
      analyser.maxDecibels = -10
    }
    
    dataArray = new Uint8Array(analyser.frequencyBinCount)
    
    return { audioContext, analyser }
  }

  /**
   * 计算当前音量 (RMS)
   */
  function calculateVolume(data) {
    let sum = 0
    for (let i = 0; i < data.length; i++) {
      sum += data[i] * data[i]
    }
    return Math.sqrt(sum / data.length) / 255
  }

  /**
   * 检测循环
   */
  function detectionLoop() {
    if (!analyser || !isListening.value) return

    analyser.getByteFrequencyData(dataArray)
    const volume = calculateVolume(dataArray)
    currentVolume.value = volume

    // 触发音量更新回调
    onVolumeUpdateCallbacks.forEach(cb => cb(volume))

    // 检测是否超过阈值
    if (volume > config.threshold) {
      // 语音检测到
      if (!isSpeechActive.value) {
        speechStartTime = Date.now()
        isSpeechActive.value = true
        silenceStartTime = null
        
        // 触发语音开始事件
        onSpeechStartCallbacks.forEach(cb => cb())
      }
    } else {
      // 音量低于阈值
      if (isSpeechActive.value) {
        // 如果还没有记录静音开始时间，记录它
        if (!silenceStartTime) {
          silenceStartTime = Date.now()
        }
        
        // 检查是否满足语音结束条件
        const silenceDuration = Date.now() - silenceStartTime
        const speechDuration = speechStartTime ? Date.now() - speechStartTime : 0
        
        if (silenceDuration >= config.endSilenceDuration && 
            speechDuration >= config.minSpeechDuration) {
          // 语音结束
          isSpeechActive.value = false
          speechStartTime = null
          silenceStartTime = null
          
          // 触发语音结束事件
          onSpeechEndCallbacks.forEach(cb => cb())
        }
      }
    }

    // 继续检测
    animationId = requestAnimationFrame(detectionLoop)
  }

  /**
   * 开始 VAD 检测
   * @param {Object} stream - MediaStream (可选，如果未提供会自动获取)
   * @returns {Promise<MediaStream>} 使用的 MediaStream
   */
  async function start(stream) {
    const { audioContext: ctx, analyser: anl } = initContext()

    // 如果没有提供流，自动获取麦克风
    if (!stream) {
      try {
        stream = await navigator.mediaDevices.getUserMedia({
          audio: {
            echoCancellation: true,
            noiseSuppression: true,
            autoGainControl: true
          }
        })
      } catch (error) {
        console.error('Failed to access microphone:', error)
        throw error
      }
    }

    microphone = ctx.createMediaStreamSource(stream)
    microphone.connect(anl)

    isListening.value = true
    isSpeechActive.value = false
    currentVolume.value = 0
    silenceStartTime = null
    speechStartTime = null

    // 开始检测循环
    detectionLoop()

    return stream
  }

  /**
   * 停止 VAD 检测
   */
  function stop() {
    isListening.value = false
    isSpeechActive.value = false
    currentVolume.value = 0

    // 取消动画帧
    if (animationId) {
      cancelAnimationFrame(animationId)
      animationId = null
    }

    // 断开麦克风连接
    if (microphone) {
      microphone.disconnect()
      microphone = null
    }

    // 重置状态
    silenceStartTime = null
    speechStartTime = null
  }

  /**
   * 设置阈值
   * @param {number} value - 新的阈值 (0-1)
   */
  function setThreshold(value) {
    config.threshold = Math.max(0, Math.min(1, value))
  }

  /**
   * 设置结束静音时间
   * @param {number} duration - 毫秒
   */
  function setEndSilenceDuration(duration) {
    config.endSilenceDuration = Math.max(100, duration)
  }

  /**
   * 注册语音开始回调
   * @param {Function} callback 
   */
  function onSpeechStart(callback) {
    onSpeechStartCallbacks.push(callback)
  }

  /**
   * 注册语音结束回调
   * @param {Function} callback 
   */
  function onSpeechEnd(callback) {
    onSpeechEndCallbacks.push(callback)
  }

  /**
   * 注册音量更新回调
   * @param {Function} callback 
   */
  function onVolumeUpdate(callback) {
    onVolumeUpdateCallbacks.push(callback)
  }

  /**
   * 获取当前配置
   */
  function getConfig() {
    return { ...config }
  }

  /**
   * 清理资源
   */
  function cleanup() {
    stop()
    
    if (audioContext) {
      audioContext.close()
      audioContext = null
    }
    
    analyser = null
    dataArray = null
  }

  onUnmounted(() => {
    cleanup()
  })

  return {
    // 状态
    isListening,
    isSpeechActive,
    currentVolume,
    
    // 方法
    start,
    stop,
    setThreshold,
    setEndSilenceDuration,
    getConfig,
    
    // 事件
    onSpeechStart,
    onSpeechEnd,
    onVolumeUpdate,
    
    // 清理
    cleanup
  }
}

export default useVAD
