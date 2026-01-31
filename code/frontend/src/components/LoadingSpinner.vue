<script setup>
import { computed } from 'vue'

const props = defineProps({
  type: {
    type: String,
    default: 'spinner',
    validator: (value) => ['spinner', 'dots', 'bar'].includes(value)
  },
  size: {
    type: String,
    default: 'medium',
    validator: (value) => ['small', 'medium', 'large'].includes(value)
  },
  color: {
    type: String,
    default: '#3498db'
  },
  text: {
    type: String,
    default: ''
  },
  fullscreen: {
    type: Boolean,
    default: false
  }
})

const sizeMap = {
  small: '24px',
  medium: '40px',
  large: '60px'
}

const spinnerSize = computed(() => sizeMap[props.size])
</script>

<template>
  <div 
    class="loading-container" 
    :class="{ 'fullscreen': fullscreen }"
    :style="{ '--loading-color': color }"
  >
    <!-- Spinner 样式 -->
    <div v-if="type === 'spinner'" class="loading-spinner" :style="{ width: spinnerSize, height: spinnerSize }">
      <svg viewBox="0 0 50 50">
        <circle 
          cx="25" 
          cy="25" 
          r="20" 
          fill="none" 
          stroke-width="4"
        />
      </svg>
    </div>

    <!-- Dots 样式 -->
    <div v-else-if="type === 'dots'" class="loading-dots">
      <span class="dot"></span>
      <span class="dot"></span>
      <span class="dot"></span>
    </div>

    <!-- Bar 样式 -->
    <div v-else-if="type === 'bar'" class="loading-bar">
      <div class="bar-progress"></div>
    </div>

    <!-- 加载文字 -->
    <p v-if="text" class="loading-text">{{ text }}</p>
  </div>
</template>

<style scoped>
.loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 20px;
}

.loading-container.fullscreen {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(255, 255, 255, 0.9);
  z-index: 9999;
}

/* Spinner 样式 */
.loading-spinner svg {
  animation: rotate 2s linear infinite;
  width: 100%;
  height: 100%;
}

.loading-spinner circle {
  stroke: var(--loading-color);
  stroke-dasharray: 80, 200;
  stroke-dashoffset: 0;
  stroke-linecap: round;
  animation: dash 1.5s ease-in-out infinite;
}

@keyframes rotate {
  100% {
    transform: rotate(360deg);
  }
}

@keyframes dash {
  0% {
    stroke-dasharray: 1, 200;
    stroke-dashoffset: 0;
  }
  50% {
    stroke-dasharray: 90, 200;
    stroke-dashoffset: -35px;
  }
  100% {
    stroke-dasharray: 90, 200;
    stroke-dashoffset: -124px;
  }
}

/* Dots 样式 */
.loading-dots {
  display: flex;
  gap: 8px;
}

.loading-dots .dot {
  width: 12px;
  height: 12px;
  background-color: var(--loading-color);
  border-radius: 50%;
  animation: bounce 1.4s ease-in-out infinite both;
}

.loading-dots .dot:nth-child(1) {
  animation-delay: -0.32s;
}

.loading-dots .dot:nth-child(2) {
  animation-delay: -0.16s;
}

.loading-dots .dot:nth-child(3) {
  animation-delay: 0;
}

@keyframes bounce {
  0%, 80%, 100% {
    transform: scale(0);
  }
  40% {
    transform: scale(1);
  }
}

/* Bar 样式 */
.loading-bar {
  width: 200px;
  height: 4px;
  background-color: #e0e0e0;
  border-radius: 2px;
  overflow: hidden;
}

.bar-progress {
  height: 100%;
  background-color: var(--loading-color);
  border-radius: 2px;
  animation: progress 1.5s ease-in-out infinite;
}

@keyframes progress {
  0% {
    width: 0%;
    margin-left: 0%;
    margin-right: 100%;
  }
  50% {
    width: 100%;
    margin-left: 0%;
    margin-right: 0%;
  }
  100% {
    width: 0%;
    margin-left: 100%;
    margin-right: 0%;
  }
}

/* 加载文字样式 */
.loading-text {
  font-size: 14px;
  color: #666;
  margin: 0;
}
</style>
