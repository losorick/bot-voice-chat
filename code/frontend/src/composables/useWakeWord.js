/**
 * 唤醒词检测 - Wake Word Detection
 * 使用 Picovoice Porcupine 实现中文唤醒词检测
 */

import { ref, onUnmounted } from 'vue'
import * as PorcupineWeb from '@picovoice/porcupine-web'
import { WebVoiceProcessor } from '@picovoice/web-voice-processor'

export function useWakeWord() {
  // 状态
  const wakeWordDetected = ref(false)
  const isListening = ref(false)
  const isInitialized = ref(false)
  const error = ref(null)
  const wakeResponseState = ref('idle') // idle | waking | recording | processing

  // 内部变量
  let porcupine = null
  let webVoiceProcessor = null

  // 事件回调
  const onWakeWordCallbacks = []
  const onWakeResponseCallbacks = [] // 唤醒响应回调
  const onErrorCallbacks = []

  // 唤醒响应状态管理
  function enterWakingState() {
    wakeResponseState.value = 'waking'
    onWakeResponseCallbacks.forEach(cb => cb('waking'))
  }

  function enterRecordingState() {
    wakeResponseState.value = 'recording'
    onWakeResponseCallbacks.forEach(cb => cb('recording'))
  }

  function enterProcessingState() {
    wakeResponseState.value = 'processing'
    onWakeResponseCallbacks.forEach(cb => cb('processing'))
  }

  function resetToIdle() {
    wakeResponseState.value = 'idle'
    onWakeResponseCallbacks.forEach(cb => cb('idle'))
  }

  /**
   * 初始化 Porcupine 引擎
   * @param {string} wakeWordPath - 唤醒词文件路径 (.ppn)
   * @param {string} modelPath - 模型文件路径 (.pv)
   * @param {Object} options - 可选配置
   */
  async function init(wakeWordPath, modelPath, options = {}) {
    const {
      sensitivity = 0.5,
      endpointDurationSec = 1.0,
      chunkLengthSec = 0.1
    } = options

    try {
      error.value = null

      // 创建 Porcupine 实例
      porcupine = await PorcupineWeb.Porcupine.create(
        [wakeWordPath],
        [modelPath],
        {
          sensitivity: [sensitivity],
          endpointDurationSec,
          chunkLengthSec
        }
      )

      isInitialized.value = true
      console.log('Porcupine initialized successfully')

      return true
    } catch (err) {
      error.value = err.message
      console.error('Failed to initialize Porcupine:', err)
      return false
    }
  }

  /**
   * 开始监听唤醒词
   * @param {MediaStream} stream - 可选的媒体流，如果不提供则自动获取麦克风
   */
  async function start(stream) {
    if (!isInitialized.value || !porcupine) {
      error.value = 'Porcupine not initialized. Call init() first.'
      console.error(error.value)
      return false
    }

    try {
      error.value = null

      // 音频处理回调
      const processAudioCallback = (audioFrame) => {
        try {
          const resultIndex = porcupine.process(audioFrame)
          if (resultIndex >= 0) {
            // 唤醒词检测到
            wakeWordDetected.value = true
            console.log('Wake word detected!')

            // 触发唤醒响应状态
            enterWakingState()
            enterRecordingState()

            // 触发回调
            onWakeWordCallbacks.forEach(cb => cb())

            // 重置状态（防止重复触发）
            setTimeout(() => {
              wakeWordDetected.value = false
            }, 2000)
          }
        } catch (err) {
          console.error('Error processing audio frame:', err)
        }
      }

      // 如果没有提供流，获取麦克风权限
      if (!stream) {
        stream = await navigator.mediaDevices.getUserMedia({
          audio: {
            echoCancellation: true,
            noiseSuppression: true,
            autoGainControl: true,
            channelCount: 1,
            sampleRate: 16000
          }
        })
      }

      // 创建 WebVoiceProcessor
      webVoiceProcessor = new WebVoiceProcessor.Builder()
        .setProcessCallback(processAudioCallback)
        .setStream(stream)
        .setEngine('porcupine')
        .setPorcupine(porcupine)
        .build()

      await webVoiceProcessor.start()
      isListening.value = true
      console.log('Wake word detection started')

      return true
    } catch (err) {
      error.value = err.message
      console.error('Failed to start wake word detection:', err)
      return false
    }
  }

  /**
   * 停止监听
   */
  function stop() {
    if (webVoiceProcessor) {
      webVoiceProcessor.stop()
      webVoiceProcessor = null
    }

    isListening.value = false
    wakeWordDetected.value = false
    console.log('Wake word detection stopped')
  }

  /**
   * 释放资源
   */
  function release() {
    stop()

    if (porcupine) {
      porcupine.release()
      porcupine = null
    }

    isInitialized.value = false
    error.value = null
    console.log('Wake word detection released')
  }

  /**
   * 注册唤醒词检测回调
   * @param {Function} callback 
   */
  function onWakeWord(callback) {
    onWakeWordCallbacks.push(callback)
  }

  /**
   * 注册唤醒响应状态回调
   * @param {Function} callback - 接收状态参数: 'waking' | 'recording' | 'processing' | 'idle'
   */
  function onWakeResponse(callback) {
    onWakeResponseCallbacks.push(callback)
  }

  /**
   * 注册错误回调
   * @param {Function} callback 
   */
  function onError(callback) {
    onErrorCallbacks.push(callback)
  }

  /**
   * 手动重置唤醒响应状态
   */
  function resetResponseState() {
    resetToIdle()
  }

  /**
   * 获取当前配置信息
   */
  function getInfo() {
    return {
      isInitialized: isInitialized.value,
      isListening: isListening.value,
      wakeWordDetected: wakeWordDetected.value,
      error: error.value,
      version: porcupine ? porcupine.version() : null
    }
  }

  // 组件卸载时自动释放资源
  onUnmounted(() => {
    release()
  })

  return {
    // 状态
    wakeWordDetected,
    isListening,
    isInitialized,
    error,
    wakeResponseState,

    // 方法
    init,
    start,
    stop,
    release,
    getInfo,
    resetResponseState,

    // 事件
    onWakeWord,
    onWakeResponse,
    onError
  }
}

export default useWakeWord
