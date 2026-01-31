import { ref, computed } from 'vue'

// 全局错误状态
const errorQueue = ref([])
const maxErrors = 3

/**
 * 全局错误状态管理
 * 提供 showError/hideError 方法
 */
export function useError() {
  /**
   * 显示错误提示
   * @param {Object} error - 错误对象
   * @param {string} error.message - 错误消息
   * @param {string} error.type - 错误类型: error, warning, info
   * @param {number} error.duration - 自动消失时间(毫秒)
   */
  function showError(error) {
    const errorItem = {
      id: Date.now() + Math.random(),
      message: error.message || '发生未知错误',
      type: error.type || 'error',
      duration: error.duration || 5000
    }

    // 限制错误队列长度
    if (errorQueue.value.length >= maxErrors) {
      errorQueue.value.shift()
    }

    errorQueue.value.push(errorItem)
  }

  /**
   * 隐藏指定错误
   * @param {number} id - 错误 ID
   */
  function hideError(id) {
    const index = errorQueue.value.findIndex(e => e.id === id)
    if (index > -1) {
      errorQueue.value.splice(index, 1)
    }
  }

  /**
   * 隐藏所有错误
   */
  function hideAllErrors() {
    errorQueue.value = []
  }

  /**
   * 获取当前显示的错误列表
   */
  function getErrors() {
    return errorQueue.value
  }

  /**
   * 是否有错误正在显示
   */
  function hasErrors() {
    return computed(() => errorQueue.value.length > 0)
  }

  return {
    errorQueue,
    showError,
    hideError,
    hideAllErrors,
    getErrors,
    hasErrors
  }
}

// 全局错误实例
export const errorHandler = useError()

/**
 * 便捷的错误创建函数
 * @param {string} message - 错误消息
 * @param {string} type - 错误类型
 * @param {number} duration - 显示时长
 */
export function createError(message, type = 'error', duration = 5000) {
  return {
    message,
    type,
    duration
  }
}

/**
 * 网络错误处理
 */
export function handleNetworkError(error) {
  let message = '网络连接失败'
  
  if (error.name === 'TypeError' && error.message.includes('fetch')) {
    message = '网络请求失败，请检查网络连接'
  } else if (error.code === 'NOT_ALLOWED') {
    message = '请允许访问麦克风'
  } else if (error.name === 'NotAllowedError') {
    message = '麦克风权限被拒绝，请在浏览器设置中允许麦克风访问'
  } else if (error.name === 'NotFoundError') {
    message = '未检测到麦克风设备'
  } else if (error.name === 'NotReadableError') {
    message = '麦克风正在被其他程序使用'
  } else if (error.message) {
    message = error.message
  }

  return createError(message, 'error', 6000)
}

/**
 * ASR 错误处理
 */
export function handleASRError(error) {
  let message = '语音识别服务异常'
  
  if (error.message?.includes('WebSocket')) {
    message = '语音识别连接失败，请稍后重试'
  } else if (error.message?.includes('timeout')) {
    message = '语音识别超时，请重试'
  } else if (error.message) {
    message = error.message
  }

  return createError(message, 'error', 6000)
}

/**
 * TTS 错误处理
 */
export function handleTTSError(error) {
  let message = '语音合成服务异常'
  
  if (error.message?.includes('401')) {
    message = '语音服务认证失败，请检查配置'
  } else if (error.message?.includes('403')) {
    message = '语音服务权限不足'
  } else if (error.message?.includes('429')) {
    message = '语音服务请求过于频繁，请稍后重试'
  } else if (error.message) {
    message = error.message
  }

  return createError(message, 'error', 6000)
}
