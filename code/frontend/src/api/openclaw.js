import axios from 'axios'
import { loading } from '../composables/useLoading'

const API_PORT = 5002

const api = axios.create({
  baseURL: `http://127.0.0.1:${API_PORT}`,
  timeout: 30000
})

// 请求拦截器 - 自动添加 API Key 到 URL 后缀（仅对需要认证的端点）
api.interceptors.request.use(
  (config) => {
    const apiKey = localStorage.getItem('api_key')
    
    if (apiKey) {
      // 只对需要认证的端点添加 API Key
      const needsAuth = config.url.includes('/api/chat') || 
                        config.url.includes('/api/models')
      if (needsAuth) {
        config.url = config.url.replace(/\/$/, '') + '/' + apiKey
      }
    }
    
    // 显示全局 loading（排除忽略 loading 的请求）
    if (!config._ignoreLoading) {
      loading.show()
    }
    
    return config
  },
  (error) => {
    loading.hideAll()
    return Promise.reject(error)
  }
)

// 响应拦截器
api.interceptors.response.use(
  (response) => {
    loading.hide()
    return response.data
  },
  (error) => {
    loading.hide()
    const message = error.response?.data?.message || error.message
    console.error('API Error:', message)
    return Promise.reject(new Error(message))
  }
)

export default api
