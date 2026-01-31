import axios from 'axios'

const API_PORT = 5002  // 后端服务端口

const api = axios.create({
  baseURL: `http://127.0.0.1:${API_PORT}`,
  timeout: 30000
})

// 请求拦截器 - 添加 API Key 认证
api.interceptors.request.use(
  (config) => {
    const apiKey = localStorage.getItem('api_key')
    if (apiKey) {
      config.headers['X-API-Key'] = apiKey
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器
api.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const message = error.response?.data?.message || error.message
    console.error('API Error:', message)
    return Promise.reject(new Error(message))
  }
)

export default api
