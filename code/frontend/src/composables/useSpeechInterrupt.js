import { ref, computed } from 'vue'

/**
 * 自适应阈值计算器
 * 动态计算环境噪音阈值，支持统计分析和定期校准
 */
class AdaptiveThreshold {
  constructor(options = {}) {
    // 配置参数
    this.thresholdOffset = options.thresholdOffset || 15 // 阈值偏移量 (dB)
    this.stdMultiplier = options.stdMultiplier || 2.5 // 标准差倍数 (N)
    this.calibrationInterval = options.calibrationInterval || 30000 // 校准间隔 (ms)
    this.noiseSampleSize = options.noiseSampleSize || 50 // 噪音采样数量
    this.minThreshold = options.minThreshold || -60 // 最小阈值 (dB)
    this.maxThreshold = options.maxThreshold || -20 // 最大阈值 (dB)

    // 状态
    this.noiseFloor = -60 // 噪音底限 (dB)
    this.threshold = -45 // 当前检测阈值 (dB)
    this.noiseSamples = [] // 噪音样本
    this.lastCalibration = Date.now()
    this.isCalibrated = false

    // 统计信息
    this.stats = {
      mean: -60,
      std: 5,
      samples: 0
    }
  }

  /**
   * 添加噪音样本
   */
  addNoiseSample(db) {
    this.noiseSamples.push(db)

    // 保持样本数量在限制内
    if (this.noiseSamples.length > this.noiseSampleSize * 2) {
      this.noiseSamples.shift()
    }

    // 定期校准
    if (Date.now() - this.lastCalibration > this.calibrationInterval) {
      this.calibrate()
    }
  }

  /**
   * 校准阈值
   */
  calibrate(samples = null) {
    const data = samples || this.noiseSamples
    if (data.length < 10) {
      console.warn('Not enough samples for calibration')
      return
    }

    // 计算均值
    const mean = this.calculateMean(data)

    // 计算标准差
    const std = this.calculateStd(data, mean)

    // 更新统计信息
    this.stats = {
      mean,
      std,
      samples: data.length
    }

    // 计算阈值: 均值 + N*标准差 + 偏移量
    let newThreshold = mean + this.stdMultiplier * std + this.thresholdOffset

    // 限制阈值范围
    newThreshold = Math.max(this.minThreshold, Math.min(this.maxThreshold, newThreshold))

    this.threshold = newThreshold
    this.noiseFloor = mean
    this.lastCalibration = Date.now()
    this.isCalibrated = true

    // 清空旧样本
    this.noiseSamples = []

    console.log(`[AdaptiveThreshold] Calibrated: threshold=${newThreshold.toFixed(2)}dB, mean=${mean.toFixed(2)}dB, std=${std.toFixed(2)}dB`)
  }

  /**
   * 计算均值
   */
  calculateMean(data) {
    if (!data || data.length === 0) return -60
    const sum = data.reduce((acc, val) => acc + val, 0)
    return sum / data.length
  }

  /**
   * 计算标准差
   */
  calculateStd(data, mean = null) {
    if (!data || data.length < 2) return 5
    const m = mean !== null ? mean : this.calculateMean(data)
    const squaredDiffs = data.map(val => Math.pow(val - m, 2))
    const avgSquaredDiff = squaredDiffs.reduce((acc, val) => acc + val, 0) / squaredDiffs.length
    return Math.sqrt(avgSquaredDiff)
  }

  /**
   * 获取当前阈值
   */
  getThreshold() {
    return this.threshold
  }

  /**
   * 获取统计信息
   */
  getStats() {
    return { ...this.stats, threshold: this.threshold, isCalibrated: this.isCalibrated }
  }

  /**
   * 重置
   */
  reset() {
    this.noiseSamples = []
    this.threshold = -45
    this.noiseFloor = -60
    this.isCalibrated = false
    this.stats = { mean: -60, std: 5, samples: 0 }
  }
}

/**
 * 音频分析工具
 */
const AudioAnalyzer = {
  /**
   * 计算 RMS (均方根) 能量
   */
  calculateRMS(dataArray) {
    let sumSquares = 0
    for (let i = 0; i < dataArray.length; i++) {
      const normalized = dataArray[i] / 255
      sumSquares += normalized * normalized
    }
    return Math.sqrt(sumSquares / dataArray.length)
  },

  /**
   * 计算过零率
   */
  calculateZeroCrossingRate(dataArray) {
    if (dataArray.length < 2) return 0
    let crossings = 0
    for (let i = 1; i < dataArray.length; i++) {
      if ((dataArray[i] >= 128 && dataArray[i - 1] < 128) ||
          (dataArray[i] < 128 && dataArray[i - 1] >= 128)) {
        crossings++
      }
    }
    return crossings / (dataArray.length - 1)
  },

  /**
   * 将 0-255 值转换为 dB (近似)
   */
  toDecibel(value) {
    if (value <= 0) return -100
    return 20 * Math.log10(value / 255)
  },

  /**
   * 将 RMS 转换为 dB
   */
  rmsToDb(rms) {
    if (rms <= 0) return -100
    return 20 * Math.log10(rms)
  }
}

/**
 * 语音打断检测 Composable (增强版)
 * 使用 Web Audio API 监听麦克风输入，检测用户语音
 * 支持自适应阈值、RMS 能量检测、过零率分析
 */
export function useSpeechInterrupt(options = {}) {
  const {
    onSpeechDetected = () => {},
    // 传统参数 (兼容)
    legacyThreshold = -50,
    checkInterval = 100,
    // 自适应阈值参数
    enableAdaptive = options.enableAdaptive !== false,
    thresholdOffset = 15,
    stdMultiplier = 2.5,
    calibrationInterval = 30000,
    // 多级检测参数
    enableMultiLevel = options.enableMultiLevel !== true,
    energyThreshold = 0.02, // RMS 能量阈值
    zcrThreshold = 0.1, // 过零率阈值
    speechConfirmCount = 2 // 连续检测次数确认
  } = options

  const isListening = ref(false)
  const speechDetected = ref(false)
  const error = ref(null)
  const currentThreshold = ref(legacyThreshold)
  const adaptiveStats = ref(null)

  let audioContext = null
  let analyser = null
  let microphoneStream = null
  let dataArray = null
  let animationFrame = null
  let checkTimer = null

  // 自适应阈值实例
  let adaptiveThreshold = null
  if (enableAdaptive) {
    adaptiveThreshold = new AdaptiveThreshold({
      thresholdOffset,
      stdMultiplier,
      calibrationInterval
    })
  }

  // 语音确认计数器
  let speechConfirmCounter = 0
  let lastSpeechTime = 0
  let isSpeechActive = false

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
          noiseSuppression: false, // 关闭噪音抑制以进行准确的噪音采样
          autoGainControl: false   // 关闭自动增益以获得准确的音量
        }
      })

      // 创建 AudioContext
      audioContext = new (window.AudioContext || window.webkitAudioContext)()
      
      // 创建分析器节点
      analyser = audioContext.createAnalyser()
      analyser.fftSize = 512
      analyser.smoothingTimeConstant = 0.8

      // 连接麦克风到分析器
      const source = audioContext.createMediaStreamSource(microphoneStream)
      source.connect(analyser)

      // 准备数据数组
      const bufferLength = analyser.frequencyBinCount
      dataArray = new Uint8Array(bufferLength)

      // 重置状态
      isListening.value = true
      speechDetected.value = false
      error.value = null
      speechConfirmCounter = 0
      isSpeechActive = false

      // 重置自适应阈值
      if (adaptiveThreshold) {
        adaptiveThreshold.reset()
      }

      // 开始检测
      detectSpeech()

      // 启动定期校准
      if (adaptiveThreshold) {
        calibrationTimer()
      }

    } catch (err) {
      console.error('Failed to start speech interrupt:', err)
      error.value = err.message || '无法访问麦克风'
      stopListening()
    }
  }

  /**
   * 定期校准
   */
  function calibrationTimer() {
    if (!isListening.value || !adaptiveThreshold) return

    // 在检测循环中进行校准采样
    calibrationTimer()
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
   * 检测语音 (增强版)
   */
  function detectSpeech() {
    if (!isListening.value) return

    // 获取音频数据
    analyser.getByteFrequencyData(dataArray)

    // 计算各项指标
    const average = calculateAverage(dataArray)
    const db = AudioAnalyzer.toDecibel(average)
    const rms = AudioAnalyzer.calculateRMS(dataArray)
    const zcr = AudioAnalyzer.calculateZeroCrossingRate(dataArray)

    // 自适应阈值模式
    if (adaptiveThreshold && adaptiveThreshold.isCalibrated) {
      currentThreshold.value = adaptiveThreshold.getThreshold()

      // 在非语音期间采样噪音
      if (!isSpeechActive && rms < energyThreshold) {
        adaptiveThreshold.addNoiseSample(db)
      }

      // 多级检测策略
      let isSpeech = false

      if (enableMultiLevel) {
        // 第一级: RMS 能量检测
        const energyPass = rms > energyThreshold

        // 第二级: 过零率分析 (语音通常有较高的过零率)
        const zcrPass = zcr > zcrThreshold && zcr < 0.5

        // 第三级: 阈值检测
        const thresholdPass = db > currentThreshold.value

        // 综合判断
        isSpeech = energyPass && zcrPass && thresholdPass
      } else {
        // 简单阈值检测
        isSpeech = db > currentThreshold.value
      }

      // 确认机制 (避免误检)
      if (isSpeech) {
        speechConfirmCounter++
        if (speechConfirmCounter >= speechConfirmCount) {
          if (!isSpeechActive) {
            isSpeechActive = true
            lastSpeechTime = Date.now()
            speechDetected.value = true
            onSpeechDetected()
          }
          speechConfirmCounter = speechConfirmCount // 保持最大值
        }
      } else {
        speechConfirmCounter = Math.max(0, speechConfirmCounter - 1)

        // 语音结束检测 (静音 500ms 后重置)
        if (isSpeechActive && Date.now() - lastSpeechTime > 500) {
          isSpeechActive = false
          speechConfirmCounter = 0
        }
      }

      // 更新统计信息
      adaptiveStats.value = adaptiveThreshold.getStats()

    } else {
      // 传统模式
      currentThreshold.value = legacyThreshold
      const isSpeech = db > legacyThreshold

      if (isSpeech) {
        speechConfirmCounter++
        if (speechConfirmCounter >= speechConfirmCount) {
          if (!isSpeechActive) {
            isSpeechActive = true
            speechDetected.value = true
            onSpeechDetected()
          }
          speechConfirmCounter = speechConfirmCount
        }
      } else {
        speechConfirmCounter = Math.max(0, speechConfirmCounter - 1)
        if (isSpeechActive && speechConfirmCounter === 0) {
          isSpeechActive = false
        }
      }
    }

    // 继续检测
    animationFrame = requestAnimationFrame(detectSpeech)
  }

  /**
   * 计算平均值
   */
  function calculateAverage(dataArray) {
    let sum = 0
    for (let i = 0; i < dataArray.length; i++) {
      sum += dataArray[i]
    }
    return sum / dataArray.length
  }

  /**
   * 获取当前音量级别 (0-1)
   */
  function getVolumeLevel() {
    if (!dataArray) return 0
    return calculateAverage(dataArray) / 255
  }

  /**
   * 获取 RMS 能量值 (0-1)
   */
  function getRMSEnergy() {
    if (!dataArray) return 0
    return AudioAnalyzer.calculateRMS(dataArray)
  }

  /**
   * 获取过零率
   */
  function getZeroCrossingRate() {
    if (!dataArray) return 0
    return AudioAnalyzer.calculateZeroCrossingRate(dataArray)
  }

  /**
   * 手动触发校准
   */
  function triggerCalibration() {
    if (adaptiveThreshold) {
      adaptiveThreshold.calibrate()
    }
  }

  /**
   * 设置临时阈值 (用于测试)
   */
  function setTemporaryThreshold(db) {
    if (adaptiveThreshold) {
      adaptiveThreshold.threshold = db
      currentThreshold.value = db
    }
  }

  return {
    isListening,
    speechDetected,
    error,
    currentThreshold,
    adaptiveStats,
    startListening,
    stopListening,
    getVolumeLevel,
    getRMSEnergy,
    getZeroCrossingRate,
    triggerCalibration,
    setTemporaryThreshold
  }
}
