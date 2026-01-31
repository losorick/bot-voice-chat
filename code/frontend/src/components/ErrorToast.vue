<script setup>
import { ref, watch, onMounted, onUnmounted } from 'vue'

const props = defineProps({
  // 是否显示
  visible: {
    type: Boolean,
    default: false
  },
  // 错误消息
  message: {
    type: String,
    default: ''
  },
  // 错误类型: error, warning, info
  type: {
    type: String,
    default: 'error',
    validator: (value) => ['error', 'warning', 'info'].includes(value)
  },
  // 自动消失时间(毫秒)，0 表示不自动消失
  duration: {
    type: Number,
    default: 5000
  },
  // 显示位置: top, bottom, center
  position: {
    type: String,
    default: 'top'
  }
})

const emit = defineEmits(['close', 'timeout'])

const timer = ref(null)

// 错误类型对应的颜色
const typeStyles = {
  error: {
    bg: '#fee2e2',
    border: '#ef4444',
    text: '#991b1b',
    icon: '❌'
  },
  warning: {
    bg: '#fef3c7',
    border: '#f59e0b',
    text: '#92400e',
    icon: '⚠️'
  },
  info: {
    bg: '#dbeafe',
    border: '#3b82f6',
    text: '#1e40af',
    icon: 'ℹ️'
  }
}

// 自动消失逻辑
watch(() => props.visible, (newVal) => {
  if (newVal && props.duration > 0) {
    startTimer()
  } else {
    stopTimer()
  }
})

const startTimer = () => {
  stopTimer()
  timer.value = setTimeout(() => {
    handleClose()
    emit('timeout')
  }, props.duration)
}

const stopTimer = () => {
  if (timer.value) {
    clearTimeout(timer.value)
    timer.value = null
  }
}

const handleClose = () => {
  stopTimer()
  emit('close')
}

// 鼠标悬停时暂停计时器
const onMouseEnter = () => {
  if (props.duration > 0) {
    stopTimer()
  }
}

const onMouseLeave = () => {
  if (props.visible && props.duration > 0) {
    startTimer()
  }
}

onUnmounted(() => {
  stopTimer()
})

// 获取当前类型的样式
const currentStyle = () => typeStyles[props.type] || typeStyles.error
</script>

<template>
  <Teleport to="body">
    <Transition name="toast">
      <div
        v-if="visible"
        class="error-toast"
        :class="[`position-${position}`]"
        :style="{
          backgroundColor: currentStyle().bg,
          borderColor: currentStyle().border,
          color: currentStyle().text
        }"
        @mouseenter="onMouseEnter"
        @mouseleave="onMouseLeave"
      >
        <span class="icon">{{ currentStyle().icon }}</span>
        <span class="message">{{ message }}</span>
        <button class="close-btn" @click="handleClose" :style="{ color: currentStyle().text }">
          ✕
        </button>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.error-toast {
  position: fixed;
  left: 50%;
  transform: translateX(-50%);
  padding: 12px 16px;
  border-radius: 8px;
  border: 1px solid;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  display: flex;
  align-items: center;
  gap: 10px;
  max-width: 90vw;
  z-index: 9999;
  font-size: 14px;
  font-weight: 500;
}

.position-top {
  top: 20px;
}

.position-bottom {
  bottom: 20px;
}

.position-center {
  top: 50%;
  transform: translate(-50%, -50%);
}

.icon {
  font-size: 16px;
  flex-shrink: 0;
}

.message {
  flex: 1;
  word-break: break-word;
  line-height: 1.4;
}

.close-btn {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 16px;
  padding: 0;
  margin-left: 8px;
  opacity: 0.6;
  transition: opacity 0.2s;
  line-height: 1;
}

.close-btn:hover {
  opacity: 1;
}

/* 动画 */
.toast-enter-active {
  animation: toast-in 0.3s ease-out;
}

.toast-leave-active {
  animation: toast-out 0.3s ease-in;
}

@keyframes toast-in {
  from {
    opacity: 0;
    transform: translateX(-50%) translateY(-20px);
  }
  to {
    opacity: 1;
    transform: translateX(-50%) translateY(0);
  }
}

@keyframes toast-out {
  from {
    opacity: 1;
    transform: translateX(-50%) translateY(0);
  }
  to {
    opacity: 0;
    transform: translateX(-50%) translateY(-20px);
  }
}

/* Center 位置特殊动画 */
.position-center.toast-enter-active {
  animation: toast-center-in 0.3s ease-out;
}

.position-center.toast-leave-active {
  animation: toast-center-out 0.3s ease-in;
}

@keyframes toast-center-in {
  from {
    opacity: 0;
    transform: translate(-50%, -50%) scale(0.9);
  }
  to {
    opacity: 1;
    transform: translate(-50%, -50%) scale(1);
  }
}

@keyframes toast-center-out {
  from {
    opacity: 1;
    transform: translate(-50%, -50%) scale(1);
  }
  to {
    opacity: 0;
    transform: translate(-50%, -50%) scale(0.9);
  }
}
</style>
