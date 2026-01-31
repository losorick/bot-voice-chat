/**
 * 阿里云 TTS (语音合成) 服务
 */

class TTSService {
  constructor() {
    this.audio = null
    this.onEnd = null
    this.onError = null
  }

  /**
   * 初始化 TTS 服务
   * @param {Object} config 配置
   * @param {string} config.appKey 阿里云 App Key
   * @param {string} config.token 访问令牌
   * @param {Function} config.onPlayEnd 播放结束回调
   * @param {Function} config.onError 错误回调
   */
  init(config) {
    this.appKey = config.appKey
    this.token = config.token
    this.onEnd = config.onEnd
    this.onError = config.onError
    this.voice = config.voice || 'siqi' // 默认音色
  }

  /**
   * 文本转语音
   * @param {string} text 要转换的文本
   */
  async speak(text) {
    try {
      // 停止当前播放
      this.stop()

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
        throw new Error('TTS request failed')
      }

      const blob = await response.blob()
      const url = URL.createObjectURL(blob)

      this.audio = new Audio(url)
      this.audio.onended = () => {
        this.onEnd?.()
        URL.revokeObjectURL(url)
      }
      this.audio.onerror = (error) => {
        this.onError?.(error)
      }

      this.audio.play()

    } catch (error) {
      console.error('TTS error:', error)
      this.onError?.(error)
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
