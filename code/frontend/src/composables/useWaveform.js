/**
 * 语音波形可视化 - 使用 Web Audio API 获取录音数据并实时绘制波形
 */

import { ref, onUnmounted } from 'vue'

export function useWaveform() {
  let audioContext = null
  let analyser = null
  let dataArray = null
  let animationId = null
  let mediaStreamSource = null

  const isVisualizing = ref(false)
  const canvasRef = ref(null)
  const canvasContext = ref(null)

  /**
   * 初始化音频上下文和分析器
   * @param {HTMLCanvasElement} canvas - Canvas 元素
   */
  function init(canvas) {
    if (!canvas) return

    canvasRef.value = canvas
    canvasContext.value = canvas.getContext('2d')

    // 设置 Canvas 尺寸
    canvas.width = canvas.offsetWidth * window.devicePixelRatio
    canvas.height = canvas.offsetHeight * window.devicePixelRatio
    canvasContext.value.scale(window.devicePixelRatio, window.devicePixelRatio)
  }

  /**
   * 连接到媒体流并开始可视化
   * @param {MediaStream} stream - 媒体流
   */
  async function startVisualization(stream) {
    if (isVisualizing.value) return

    try {
      // 创建音频上下文
      if (!audioContext) {
        audioContext = new (window.AudioContext || window.webkitAudioContext)()
      }

      // 创建分析器
      analyser = audioContext.createAnalyser()
      analyser.fftSize = 2048
      analyser.smoothingTimeConstant = 0.8

      // 连接媒体流到分析器
      mediaStreamSource = audioContext.createMediaStreamSource(stream)
      mediaStreamSource.connect(analyser)

      // 创建数据数组
      dataArray = new Uint8Array(analyser.frequencyBinCount)

      isVisualizing.value = true

      // 开始绘制波形
      drawWaveform()
    } catch (error) {
      console.error('Failed to start waveform visualization:', error)
    }
  }

  /**
   * 绘制波形
   */
  function drawWaveform() {
    if (!isVisualizing.value || !canvasContext.value || !analyser) return

    const ctx = canvasContext.value
    const canvas = canvasRef.value

    if (!ctx || !canvas) return

    // 获取音频数据
    analyser.getByteTimeDomainData(dataArray)

    // 清空画布
    ctx.clearRect(0, 0, canvas.width / window.devicePixelRatio, canvas.height / window.devicePixelRatio)

    // 设置波形样式
    ctx.lineWidth = 2
    ctx.strokeStyle = getWaveformColor()
    ctx.lineCap = 'round'
    ctx.lineJoin = 'round'

    // 绘制波形
    const width = canvas.width / window.devicePixelRatio
    const height = canvas.height / window.devicePixelRatio
    const sliceWidth = width / dataArray.length
    let x = 0

    ctx.beginPath()

    for (let i = 0; i < dataArray.length; i++) {
      const v = dataArray[i] / 128.0
      const y = (v * height) / 2

      if (i === 0) {
        ctx.moveTo(x, y)
      } else {
        ctx.lineTo(x, y)
      }

      x += sliceWidth
    }

    ctx.lineTo(width, height / 2)
    ctx.stroke()

    // 继续动画
    animationId = requestAnimationFrame(drawWaveform)
  }

  /**
   * 获取波形颜色
   */
  function getWaveformColor() {
    // 可以根据状态返回不同颜色
    return '#667eea'
  }

  /**
   * 设置波形颜色
   * @param {string} color - 颜色值
   */
  function setWaveformColor(color) {
    if (canvasContext.value) {
      canvasContext.value.strokeStyle = color
    }
  }

  /**
   * 停止可视化
   */
  function stopVisualization() {
    isVisualizing.value = false

    if (animationId) {
      cancelAnimationFrame(animationId)
      animationId = null
    }

    // 断开媒体流连接
    if (mediaStreamSource) {
      mediaStreamSource.disconnect()
      mediaStreamSource = null
    }

    // 清空画布
    if (canvasContext.value && canvasRef.value) {
      canvasContext.value.clearRect(
        0,
        0,
        canvasRef.value.width / window.devicePixelRatio,
        canvasRef.value.height / window.devicePixelRatio
      )
    }
  }

  /**
   * 清理资源
   */
  function cleanup() {
    stopVisualization()

    if (audioContext) {
      audioContext.close()
      audioContext = null
    }

    analyser = null
    dataArray = null
    canvasRef.value = null
    canvasContext.value = null
  }

  onUnmounted(() => {
    cleanup()
  })

  return {
    isVisualizing,
    init,
    startVisualization,
    stopVisualization,
    setWaveformColor,
    cleanup
  }
}
