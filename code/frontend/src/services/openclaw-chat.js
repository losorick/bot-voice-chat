/**
 * OpenClaw 会话对话服务
 * 通过 OpenClaw subagent 处理语音对话
 */

class OpenClawService {
  constructor() {
    this.baseUrl = 'http://localhost:5002'
    this.label = 'voice-chat'
  }

  /**
   * 创建新的对话会话并获取回复
   * @param {string} message 用户消息
   * @returns {Promise<object>} { reply, tts_summary, tts_audio }
   */
  async chat(message) {
    try {
      const response = await fetch(`${this.baseUrl}/api/v1/openclaw/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          message: message,
          session_label: this.label,
          need_tts: true
        })
      })

      if (!response.ok) {
        // #region agent log
        if (response.status === 500) {
          fetch('http://127.0.0.1:7242/ingest/9fd31da4-8c90-45ce-8957-81ce326dde6d', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ location: 'openclaw-chat.js:chat', message: 'openclaw/chat 500', data: { status: 500, url: `${this.baseUrl}/api/v1/openclaw/chat` }, timestamp: Date.now(), sessionId: 'debug-session', hypothesisId: 'A' }) }).catch(() => {})
        }
        // #endregion
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.error || `请求失败: ${response.status}`)
      }

      const data = await response.json()
      
      if (data.success) {
        return {
          reply: data.reply || '',
          ttsSummary: data.tts_summary || '',
          ttsAudio: data.tts_audio || null
        }
      } else {
        throw new Error(data.error || '响应格式异常')
      }
    } catch (error) {
      console.error('OpenClaw chat error:', error)
      throw error
    }
  }
}

export default new OpenClawService()
