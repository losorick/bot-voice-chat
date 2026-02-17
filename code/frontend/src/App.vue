<script setup>
import { ref, watch } from 'vue'
import { RouterView } from 'vue-router'
import LoadingSpinner from './components/LoadingSpinner.vue'
import ErrorToast from './components/ErrorToast.vue'
import { loading } from './composables/useLoading'
import { errorHandler } from './composables/useError'

// 关闭错误提示
function handleErrorClose(errorId) {
  errorHandler.hideError(errorId)
}
</script>

<template>
  <div class="app-container">
    <!-- 全局 Loading -->
    <Transition name="fade">
      <LoadingSpinner 
        v-if="loading.isLoading()"
        type="spinner"
        size="large"
        color="#3498db"
        :text="loading.loadingText"
        fullscreen
      />
    </Transition>
    
    <!-- 错误提示 -->
    <ErrorToast
      v-for="error in errorHandler.errorQueue.value"
      :key="error.id"
      :visible="true"
      :message="error.message"
      :type="error.type"
      :duration="error.duration"
      @close="handleErrorClose(error.id)"
    />
    
    <!-- 主内容区 -->
    <main class="main-content">
      <RouterView />
    </main>
  </div>
</template>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  background: #f5f5f5;
}

.app-container {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.main-content {
  flex: 1;
}

/* 动画 */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.slide-down-enter-active,
.slide-down-leave-active {
  transition: all 0.3s ease;
  overflow: hidden;
}

.slide-down-enter-from,
.slide-down-leave-to {
  opacity: 0;
  max-height: 0;
  padding-top: 0;
  padding-bottom: 0;
}
</style>
