/**
 * 阿里云 ASR (语音识别) 服务
 * 支持实时语音识别
 */

class ASRService {
  constructor() {
    this.isRecording = false
    this.mediaRecorder = null
    this.audioContext = null
    this.websocket = null
    this.onTranscript = null
    this.onError = null
  }

  /**
   * 初始化 ASR 服务
   * @param {Object} config 配置
   * @param {string} config.appKey 阿里云 App Key
   * @param {Function} config.onTranscript 实时转写回调
   * @param {Function} config.onError 错误回调
   */
  init(config) {
    this.appKey = config.appKey
    this.onTranscript = config.onTranscript
    this.onError = config.onError
  }

  /**
   * 开始录音和识别
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
        mimeType: 'audio/webm'
      })

      // 创建 WebSocket 连接
      this.createWebSocket()

      this.mediaRecorder.ondataavailable = (event) => {
        if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
          this.websocket.send(event.data)
        }
      }

      this.mediaRecorder.start(3000) // 每3秒发送一次音频数据
      this.isRecording = true

    } catch (error) {
      console.error('ASR start error:', error)
      this.onError?.(error)
    }
  }

  /**
   * 创建 WebSocket 连接
   */
  createWebSocket() {
    // 阿里云实时语音识别 WebSocket URL
    const url = `wss://nls-gateway.cn-shanghai.aliyuncs.com/ws/v1?token=${this.getToken()}`
    
    this.websocket = new WebSocket(url, ['oss'])

    this.websocket.onopen = () => {
      // 发送开始事件
      this.websocket.send(JSON.stringify({
        header: {
          namespace: 'SpeechTranscriber',
          name: 'StartTranscription',
          appkey: this.appKey
        },
        payload: {
          format: 'pcm',
          sample_rate: 16000,
          enable_intermediate_result: true,
          enable_punctuation_prediction: true,
          enableInverseTextNormalization: true
        }
      }))
    }

    this.websocket.onmessage = (event) => {
      const data = JSON.parse(event.data)
      
      if (data.header.name === 'TranscriptionResultChanged') {
        // 中间结果
        this.onTranscript?.(data.payload.result)
      } else if (data.header.name === 'TranscriptionCompleted') {
        // 最终结果
        this.onTranscript?.(data.payload.result, true)
      }
    }

    this.websocket.onerror = (error) => {
      console.error('WebSocket error:', error)
      this.onError?.(error)
    }

    this.websocket.onclose = () => {
      console.log('WebSocket closed')
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

    if (this.websocket) {
      this.websocket.send(JSON.stringify({
        header: {
          namespace: 'SpeechTranscriber',
          name: 'StopTranscription'
        }
      }))
      this.websocket.close()
    }

    if (this.audioContext) {
      this.audioContext.close()
    }

    this.isRecording = false
  }

  /**
   * 获取 Token (实际项目中应该从后端获取)
   */
  getToken() {
    // 这里需要从后端 API 获取 Token
    return localStorage.getItem('aliyun_token') || ''
  }
}

export default new ASRService()
