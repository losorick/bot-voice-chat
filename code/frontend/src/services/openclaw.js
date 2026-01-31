/**
 * 后端 API 通信服务
 */

import api from '../api/openclaw'

class BackendService {
  constructor() {
    this.baseUrl = 'http://127.0.0.1:5002'
  }

  /**
   * 获取带 API Key 的 URL
   */
  getApiUrl(endpoint) {
    const apiKey = localStorage.getItem('api_key')
    if (apiKey) {
      return `${this.baseUrl}${endpoint}/${apiKey}`
    }
    return `${this.baseUrl}${endpoint}`
  }

  /**
   * 验证 API Key
   * @param {string} apiKey 
   * @returns {Promise<boolean>}
   */
  async verifyKey(apiKey) {
    try {
      const response = await fetch(this.getApiUrl('/api/chat'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          messages: [{ role: 'user', content: 'test' }],
          max_tokens: 1
        })
      })

      if (response.ok) {
        return { success: true }
      } else {
        const data = await response.json()
        return { success: false, error: data.message || '验证失败' }
      }
    } catch (error) {
      return { success: false, error: error.message || '网络错误' }
    }
  }

  /**
   * 发送消息并获取回复
   * @param {string} message 用户消息
   * @returns {Promise<string>} AI 回复
   */
  async sendMessage(message) {
    try {
      const response = await api.post('/api/chat', {
        messages: [{ role: 'user', content: message }]
      })
      
      if (response.success) {
        return response.data?.output?.text || ''
      } else {
        throw new Error(response.error || '请求失败')
      }
    } catch (error) {
      console.error('sendMessage error:', error)
      throw error
    }
  }

  /**
   * 获取支持的模型列表
   */
  async getModels() {
    try {
      const response = await api.get('/api/models')
      return response
    } catch (error) {
      console.error('getModels error:', error)
      return { models: [], default: 'qwen-turbo' }
    }
  }
}

export default new BackendService()
