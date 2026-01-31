/**
 * 音频分析器 - 用于检测音量并控制 Live2D 口型
 */

import { ref, onUnmounted } from 'vue'

export function useAudioAnalyzer() {
  let audioContext = null
  let analyser = null
  let dataArray = null
  let animationId = null

  /**
   * 初始化音频上下文
   */
  function initAudioContext() {
    if (!audioContext) {
      audioContext = new (window.AudioContext || window.webkitAudioContext)()
    }
    return audioContext
  }

  /**
   * 分析音频并实时回调音量值
   * @param {HTMLAudioElement} audio - Audio 元素
   * @param {Function} onVolume - 音量回调 (value: 0-1)
   */
  function analyzeAudio(audio, onVolume) {
    const context = initAudioContext()
    
    // 创建分析器
    analyser = context.createAnalyser()
    analyser.fftSize = 256
    
    // 连接音频源
    const source = context.createMediaElementSource(audio)
    source.connect(analyser)
    analyser.connect(context.destination)
    
    dataArray = new Uint8Array(analyser.frequencyBinCount)
    
    function update() {
      if (!analyser) return
      
      analyser.getByteFrequencyData(dataArray)
      
      // 计算平均音量
      const average = dataArray.reduce((a, b) => a + b, 0) / dataArray.length
      
      // 归一化到 0-1
      const normalizedVolume = average / 255
      
      // 调用回调
      onVolume(normalizedVolume)
      
      // 继续分析
      animationId = requestAnimationFrame(update)
    }
    
    update()
  }

  /**
   * 获取瞬时嘴巴开合度（基于音量）
   */
  function getMouthOpenness() {
    if (!analyser || !dataArray) return 0
    
    analyser.getByteFrequencyData(dataArray)
    const average = dataArray.reduce((a, b) => a + b, 0) / dataArray.length
    return average / 255
  }

  /**
   * 清理资源
   */
  function cleanup() {
    if (animationId) {
      cancelAnimationFrame(animationId)
    }
    if (audioContext) {
      audioContext.close()
      audioContext = null
    }
    analyser = null
    dataArray = null
  }

  onUnmounted(() => {
    cleanup()
  })

  return {
    analyzeAudio,
    getMouthOpenness,
    cleanup
  }
}

/**
 * 简单的音量检测（不需要 AudioContext）
 */
export function useSimpleVolume() {
  let audioElement = null

  /**
   * 开始监听音量
   */
  function startListening(audioEl, onVolume) {
    audioElement = audioEl
    
    audioElement.addEventListener('timeupdate', () => {
      // 简化版：基于当前时间戳的随机波动模拟
      // 实际项目中应该使用 Web Audio API
      const baseVolume = Math.random() * 0.3
      const timeBased = Math.sin(Date.now() / 100) * 0.2
      onVolume(Math.max(0, Math.min(1, baseVolume + timeBased + 0.3)))
    })
  }

  /**
   * 停止监听
   */
  function stopListening() {
    if (audioElement) {
      audioElement.removeEventListener('timeupdate', () => {})
      audioElement = null
    }
  }

  return {
    startListening,
    stopListening
  }
}
