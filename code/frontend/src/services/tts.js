import { errorHandler, handleTTSError, handleNetworkError } from '../composables/useError'
import { useSpeechInterrupt } from '../composables/useSpeechInterrupt'

/**
 * 阿里云 TTS (语音合成) 服务
 */

class TTSService {
  constructor() {
    this.audio = null
    this.onEnd = null
    this.onError = null
    this.onSpeechInterrupt = null
    this.speechInterrupt = null
    this.isPlaying = false
  }

  /**
   * 初始化 TTS 服务
   * @param {Object} config 配置
   * @param {string} config.appKey 阿里云 App Key
   * @param {string} config.token 访问令牌
   * @param {Function} config.onPlayEnd 播放结束回调
   * @param {Function} config.onError 错误回调
   * @param {Function} config.onSpeechInterrupt 语音打断回调
   */
  init(config) {
    this.appKey = config.appKey
    this.token = config.token
    this.onEnd = config.onEnd
    this.onError = config.onError
    this.onSpeechInterrupt = config.onSpeechInterrupt
    this.voice = config.voice || 'siqi' // 默认音色

    // 初始化语音打断检测
    this.speechInterrupt = useSpeechInterrupt({
      threshold: -50,
      onSpeechDetected: () => this.handleSpeechInterrupt()
    })
  }

  /**
   * 处理语音打断
   */
  handleSpeechInterrupt() {
    console.log('Speech interrupt detected!')
    
    // 停止 TTS 播放
    this.stop()
    
    // 触发打断回调
    if (this.onSpeechInterrupt) {
      this.onSpeechInterrupt()
    }
  }

  /**
   * 启用语音打断检测
   */
  enableSpeechInterrupt() {
    if (!this.speechInterrupt) return
    this.speechInterrupt.startListening()
  }

  /**
   * 禁用语音打断检测
   */
  disableSpeechInterrupt() {
    if (!this.speechInterrupt) return
    this.speechInterrupt.stopListening()
  }

  /**
   * 文本转语音
   * @param {string} text 要转换的文本
   */
  async speak(text) {
    try {
      // 停止当前播放
      this.stop()

      // 启用语音打断检测
      this.isPlaying = true
      this.enableSpeechInterrupt()

      // 阿里云 TTS API 调用
      const response = await fetch(
        `https://nls-gateway.cn-shanghai.aliyuncs.com/rest/v1/tts?appkey=${this.appKey}`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${this.token}`
          },
          body: JSON.stringify({
            text,
            format: 'mp3',
            sample_rate: 16000,
            voice: this.voice,
            volume: 50,
            speech_rate: 0,
            pitch_rate: 0
          })
        }
      )

      if (!response.ok) {
        const error = new Error('TTS request failed')
        error.code = response.status
        throw error
      }

      const blob = await response.blob()
      const url = URL.createObjectURL(blob)

      this.audio = new Audio(url)
      this.audio.onended = () => {
        this.isPlaying = false
        this.disableSpeechInterrupt()
        this.onEnd?.()
        URL.revokeObjectURL(url)
      }
      this.audio.onerror = (error) => {
        this.isPlaying = false
        this.disableSpeechInterrupt()
        const handledError = handleNetworkError(error)
        this.onError?.(error)
        errorHandler.showError(handledError)
      }

      this.audio.play()

    } catch (error) {
      this.isPlaying = false
      this.disableSpeechInterrupt()
      console.error('TTS error:', error)
      const handledError = error.code ? handleTTSError(error) : handleNetworkError(error)
      this.onError?.(error)
      errorHandler.showError(handledError)
    }
  }

  /**
   * 停止播放
   */
  stop() {
    if (this.audio) {
      this.audio.pause()
      this.audio.currentTime = 0
      this.audio = null
    }
  }
}

export default new TTSService()
