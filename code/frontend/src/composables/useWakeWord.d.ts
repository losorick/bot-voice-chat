/**
 * 唤醒词检测 Hook - TypeScript 类型定义
 * Wake Word Detection Hook Type Definitions
 */

import { Ref } from 'vue'

/**
 * 唤醒响应状态类型
 */
export type WakeResponseState = 'idle' | 'waking' | 'recording' | 'processing'

/**
 * 唤醒词检测配置选项
 */
export interface WakeWordOptions {
  /** 灵敏度 (0-1)，值越高越灵敏，误检率也越高 */
  sensitivity?: number
  /** 端点持续时间（秒） */
  endpointDurationSec?: number
  /** 音频块长度（秒） */
  chunkLengthSec?: number
  /** Picovoice Access Key（如果需要） */
  accessKey?: string
}

/**
 * 唤醒词检测信息
 */
export interface WakeWordInfo {
  isInitialized: boolean
  isListening: boolean
  wakeWordDetected: boolean
  error: string | null
  version: string | null
}

/**
 * 唤醒词检测 Hook 返回值
 */
export interface UseWakeWordReturn {
  // 状态
  wakeWordDetected: Ref<boolean>
  isListening: Ref<boolean>
  isInitialized: Ref<boolean>
  error: Ref<string | null>
  wakeResponseState: Ref<WakeResponseState>

  // 方法
  init: (wakeWordPath: string, options?: WakeWordOptions) => Promise<boolean>
  start: (stream?: MediaStream) => Promise<boolean>
  stop: () => void
  release: () => void
  getInfo: () => WakeWordInfo
  resetResponseState: () => void

  // 事件
  onWakeWord: (callback: () => void) => void
  onWakeResponse: (callback: (state: WakeResponseState) => void) => void
  onError: (callback: (error: Error) => void) => void
}

export default UseWakeWordReturn
