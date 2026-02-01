import { errorHandler, handleASRError, handleNetworkError } from '../composables/useError'

/**
 * 阿里云 ASR (语音识别) 服务
 * 使用 DashScope 语音识别 API
 */

class ASRService {
  constructor() {
    this.isRecording = false
    this.mediaRecorder = null
    this.audioContext = null
    this.audioChunks = []
    this.onTranscript = null
    this.onError = null
    this.onStatusChange = null
  }

  /**
   * 初始化 ASR 服务
   * @param {Object} config 配置
   * @param {Function} config.onTranscript 转写回调
   * @param {Function} config.onError 错误回调
   * @param {Function} config.onStatusChange 状态变化回调
   */
  init(config) {
    this.onTranscript = config.onTranscript
    this.onError = config.onError
    this.onStatusChange = config.onStatusChange
  }

  /**
   * 开始录音
   */
  async start() {
    try {
      // 获取麦克风权限
      const stream = await navigator.mediaDevices.getUserMedia({ 
        audio: {
          sampleRate: 16000,
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true
        }
      })

      this.audioContext = new (window.AudioContext || window.webkitAudioContext)({
        sampleRate: 16000
      })

      const source = this.audioContext.createMediaStreamSource(stream)
      this.mediaRecorder = new MediaRecorder(stream, {
        mimeType: 'audio/webm;codecs=opus'
      })

      this.audioChunks = []

      this.mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          this.audioChunks.push(event.data)
        }
      }

      this.mediaRecorder.onstop = async () => {
        // 将录音发送到后端进行识别
        await this.recognize()
      }

      this.mediaRecorder.start(100) // 每100ms录制一次
      this.isRecording = true
      this.onStatusChange?.('recording')

    } catch (error) {
      console.error('ASR start error:', error)
      const handledError = handleNetworkError(error)
      this.onError?.(error)
      errorHandler.showError(handledError)
    }
  }

  /**
   * 发送录音到后端进行识别
   */
  async recognize() {
    try {
      const audioBlob = new Blob(this.audioChunks, { type: 'audio/webm' })
      this.audioChunks = [] // 清空缓存

      // 创建 FormData
      const formData = new FormData()
      formData.append('file', audioBlob, 'recording.webm')
      formData.append('model', 'fun-asr-mtl') // 使用 DashScope Fun-ASR 模型

      // 调用后端语音识别接口
      const response = await fetch('http://localhost:5002/api/v1/asr/recognize', {
        method: 'POST',
        body: formData
      })

      if (!response.ok) {
        throw new Error('语音识别请求失败')
      }

      const result = await response.json()

      if (result.success && result.text) {
        this.onTranscript?.(result.text, true)
      }

    } catch (error) {
      console.error('ASR recognize error:', error)
      // 如果后端接口不可用，回退到提示用户
      errorHandler.showError({
        message: '语音识别服务暂时不可用，请使用文字输入',
        type: 'warning',
        duration: 3000
      })
    }
  }

  /**
   * 停止录音
   */
  stop() {
    if (this.mediaRecorder && this.isRecording) {
      this.mediaRecorder.stop()
      this.mediaRecorder.stream.getTracks().forEach(track => track.stop())
    }

    if (this.audioContext) {
      this.audioContext.close()
    }

    this.isRecording = false
    this.onStatusChange?.('stopped')
  }

  /**
   * 获取当前录音状态
   */
  get isActive() {
    return this.isRecording
  }
}

export default new ASRService()
