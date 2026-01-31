<script setup>
import { ref, watch } from 'vue'
import { RouterView } from 'vue-router'
import TaskStatusCard from './components/TaskStatusCard.vue'
import LoadingSpinner from './components/LoadingSpinner.vue'
import { loading } from './composables/useLoading'

const showTaskStatus = ref(true)

function toggleTaskStatus() {
  showTaskStatus.value = !showTaskStatus.value
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
    
    <!-- 任务状态栏（可折叠） -->
    <div class="task-status-section" :class="{ collapsed: !showTaskStatus }">
      <button class="toggle-btn" @click="toggleTaskStatus">
        {{ showTaskStatus ? '📊 隐藏任务状态' : '📊 显示任务状态' }}
      </button>
      
      <Transition name="slide-down">
        <div v-if="showTaskStatus" class="task-status-wrapper">
          <TaskStatusCard />
        </div>
      </Transition>
    </div>
    
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

.task-status-section {
  background: #f0f0f0;
  padding: 0 16px;
  transition: all 0.3s;
}

.task-status-section.collapsed {
  padding: 8px 16px;
  background: #e8e8e8;
}

.toggle-btn {
  padding: 6px 12px;
  background: transparent;
  border: none;
  font-size: 12px;
  color: #666;
  cursor: pointer;
  opacity: 0.7;
  transition: opacity 0.2s;
}

.toggle-btn:hover {
  opacity: 1;
}

.task-status-wrapper {
  padding: 8px 0 16px;
  max-width: 600px;
  margin: 0 auto;
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
