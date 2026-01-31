import { ref } from 'vue'

const loadingCount = ref(0)
const loadingText = ref('')

export function useLoading() {
  /**
   * 显示 loading
   * @param {string} text - 可选的 loading 提示文字
   */
  function show(text = '') {
    loadingCount.value++
    loadingText.value = text
  }

  /**
   * 隐藏 loading
   */
  function hide() {
    if (loadingCount.value > 0) {
      loadingCount.value--
    }
    if (loadingCount.value === 0) {
      loadingText.value = ''
    }
  }

  /**
   * 强制隐藏所有 loading
   */
  function hideAll() {
    loadingCount.value = 0
    loadingText.value = ''
  }

  /**
   * 是否正在 loading
   */
  function isLoading() {
    return loadingCount.value > 0
  }

  return {
    loadingCount,
    loadingText,
    show,
    hide,
    hideAll,
    isLoading
  }
}

// 全局 loading 实例
export const loading = useLoading()
