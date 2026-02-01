import { errorHandler, handleTTSError, handleNetworkError } from '../composables/useError'
import { useSpeechInterrupt } from '../composables/useSpeechInterrupt'

/**
 * DashScope TTS (语音合成) 服务
 * 使用阿里云 DashScope cosyvoice-v3-flash 模型
 */

class TTSService {
  constructor() {
    this.audio = null
    this.onEnd = null
    this.onError = null
    this.onSpeechInterrupt = null
    this.speechInterrupt = null
    this.isPlaying = false
    this.baseUrl = 'http://localhost:5002'
  }

  /**
   * 初始化 TTS 服务
   * @param {Object} config 配置
   * @param {string} config.voice 音色 (默认: longanyang)
   * @param {Function} config.onPlayEnd 播放结束回调
   * @param {Function} config.onError 错误回调
   * @param {Function} config.onSpeechInterrupt 语音打断回调
   */
  init(config) {
    this.voice = config.voice || 'longanyang'
    this.onEnd = config.onEnd
    this.onError = config.onError
    this.onSpeechInterrupt = config.onSpeechInterrupt

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
    this.stop()
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

      // 调用后端 DashScope TTS API
      const response = await fetch(`${this.baseUrl}/api/v1/tts/synthesize`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          text: text,
          voice: this.voice,
          format: 'pcm_22050hz_mono_16bit'
        })
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        const error = new Error(errorData.error || 'TTS request failed')
        error.code = response.status
        throw error
      }

      const blob = await response.blob()
      const url = URL.createObjectURL(blob)

      const audio = new Audio(url)
      this.audio = audio
      
      audio.oncanplaythrough = () => {
        console.log('TTS: Audio can play through, starting playback')
        audio.play().catch(err => {
          console.error('TTS play() failed:', err)
          this.isPlaying = false
          this.disableSpeechInterrupt()
        })
      }
      
      audio.onended = () => {
        this.isPlaying = false
        this.disableSpeechInterrupt()
        this.onEnd?.()
        URL.revokeObjectURL(url)
      }
      audio.onerror = (error) => {
        console.error('TTS audio error:', error)
        this.isPlaying = false
        this.disableSpeechInterrupt()
        const handledError = handleNetworkError(error)
        this.onError?.(error)
        errorHandler.showError(handledError)
      }

      // 预加载音频
      audio.load()

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
