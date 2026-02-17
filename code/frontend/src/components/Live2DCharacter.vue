<script setup>
import { ref, onMounted, onUnmounted } from 'vue'

const props = defineProps({
  autoPlay: {
    type: Boolean,
    default: true
  }
})

const emit = defineEmits(['loaded', 'error'])

const iframeRef = ref(null)
const isLoading = ref(true)

// 监听 iframe 加载完成
function handleIframeLoad() {
  isLoading.value = false
  emit('loaded', true)
}

// 暴露方法
defineExpose({
  get iframe() { return iframeRef.value },
  startSpeaking() {
    // 暂时未实现 Live2D 说话动画
    console.log('Live2D: startSpeaking called')
  },
  stopSpeaking() {
    // 暂时未实现 Live2D 说话动画
    console.log('Live2D: stopSpeaking called')
  }
})

onMounted(() => {
  // iframe 会自动加载
})
</script>

<template>
  <div class="live2d-container">
    <!-- 加载状态 -->
    <div v-if="isLoading" class="loading-overlay">
      <div class="loading-spinner"></div>
      <p>加载 Live2D 中...</p>
    </div>
    
    <!-- Live2D iframe -->
    <iframe 
      ref="iframeRef"
      src="/live2d-standalone.html"
      class="live2d-iframe"
      @load="handleIframeLoad"
      frameborder="0"
      allowfullscreen
    ></iframe>
  </div>
</template>

<style scoped>
.live2d-container {
  position: relative;
  width: 100%;
  height: 100%;
  background: linear-gradient(180deg, #f5f5f5 0%, #e8e8e8 100%);
  border-radius: 20px;
  overflow: hidden;
  box-shadow: 0 10px 40px rgba(0,0,0,0.1);
}

.live2d-iframe {
  width: 100%;
  height: 100%;
  border: none;
  background: transparent;
}

.loading-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: rgba(255,255,255,0.95);
  z-index: 10;
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 3px solid #f0f0f0;
  border-top-color: #ff6b9d;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.loading-overlay p {
  margin-top: 16px;
  color: #666;
  font-size: 14px;
}
</style>
