import { ref } from 'vue'

/**
 * 语音打断检测 Composable
 * 使用 Web Audio API 监听麦克风输入，检测用户语音
 */
export function useSpeechInterrupt(options = {}) {
  const {
    onSpeechDetected = () => {},
    threshold = -50, // 音量阈值 (dB)
    checkInterval = 100 // 检测间隔 (ms)
  } = options

  const isListening = ref(false)
  const speechDetected = ref(false)
  const error = ref(null)

  let audioContext = null
  let analyser = null
  let microphoneStream = null
  let dataArray = null
  let animationFrame = null
  let checkTimer = null

  /**
   * 开始监听麦克风
   */
  async function startListening() {
    if (isListening.value) return

    try {
      // 请求麦克风权限
      microphoneStream = await navigator.mediaDevices.getUserMedia({ 
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true
        }
      })

      // 创建 AudioContext
      audioContext = new (window.AudioContext || window.webkitAudioContext)()
      
      // 创建分析器节点
      analyser = audioContext.createAnalyser()
      analyser.fftSize = 256
      analyser.smoothingTimeConstant = 0.8

      // 连接麦克风到分析器
      const source = audioContext.createMediaStreamSource(microphoneStream)
      source.connect(analyser)

      // 准备数据数组
      const bufferLength = analyser.frequencyBinCount
      dataArray = new Uint8Array(bufferLength)

      // 开始检测
      isListening.value = true
      speechDetected.value = false
      error.value = null

      detectSpeech()

    } catch (err) {
      console.error('Failed to start speech interrupt:', err)
      error.value = err.message || '无法访问麦克风'
      stopListening()
    }
  }

  /**
   * 停止监听
   */
  function stopListening() {
    isListening.value = false
    speechDetected.value = false

    // 取消动画帧
    if (animationFrame) {
      cancelAnimationFrame(animationFrame)
      animationFrame = null
    }

    // 清除检测定时器
    if (checkTimer) {
      clearTimeout(checkTimer)
      checkTimer = null
    }

    // 关闭音频上下文
    if (audioContext) {
      audioContext.close()
      audioContext = null
    }

    // 停止麦克风流
    if (microphoneStream) {
      microphoneStream.getTracks().forEach(track => track.stop())
      microphoneStream = null
    }

    analyser = null
    dataArray = null
  }

  /**
   * 检测语音
   */
  function detectSpeech() {
    if (!isListening.value) return

    // 获取音频数据
    analyser.getByteFrequencyData(dataArray)

    // 计算平均音量
    let sum = 0
    for (let i = 0; i < dataArray.length; i++) {
      sum += dataArray[i]
    }
    const average = sum / dataArray.length

    // 将 0-255 的值转换为 dB (近似)
    // 0 = -∞ dB, 255 = 0 dB
    const db = average > 0 ? 20 * Math.log10(average / 255) : -100

    // 检测到语音（超过阈值）
    if (db > threshold) {
      speechDetected.value = true
      onSpeechDetected()

      // 重置检测状态
      speechDetected.value = false
    }

    // 继续检测
    animationFrame = requestAnimationFrame(detectSpeech)
  }

  /**
   * 获取当前音量级别 (0-1)
   */
  function getVolumeLevel() {
    if (!dataArray) return 0

    let sum = 0
    for (let i = 0; i < dataArray.length; i++) {
      sum += dataArray[i]
    }
    return sum / dataArray.length / 255
  }

  return {
    isListening,
    speechDetected,
    error,
    startListening,
    stopListening,
    getVolumeLevel
  }
}
