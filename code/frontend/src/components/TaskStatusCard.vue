<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import api from '../api/openclaw'

const props = defineProps({
  autoRefresh: {
    type: Boolean,
    default: true
  },
  refreshInterval: {
    type: Number,
    default: 3000  // 3秒
  }
})

const emit = defineEmits(['task-click'])

// 统计数据
const statistics = ref({
  total: 0,
  pending: 0,
  processing: 0,
  completed: 0,
  failed: 0
})

// 正在处理的任务
const activeTasks = ref([])
const recentTasks = ref([])

const isLoading = ref(false)
const error = ref(null)
let refreshTimer = null

/**
 * 获取任务统计
 */
async function fetchStatistics() {
  try {
    const response = await api.get('/api/tasks/statistics')
    if (response.success) {
      statistics.value = response.statistics
    }
  } catch (e) {
    console.error('Failed to fetch statistics:', e)
  }
}

/**
 * 获取活跃任务
 */
async function fetchActiveTasks() {
  try {
    const response = await api.get('/api/tasks/active')
    if (response.success) {
      activeTasks.value = response.tasks
    }
  } catch (e) {
    console.error('Failed to fetch active tasks:', e)
  }
}

/**
 * 获取最近任务
 */
async function fetchRecentTasks() {
  try {
    const response = await api.get('/api/tasks?limit=5')
    if (response.success) {
      recentTasks.value = response.tasks
    }
  } catch (e) {
    console.error('Failed to fetch recent tasks:', e)
  }
}

/**
 * 刷新所有数据
 */
async function refresh() {
  isLoading.value = true
  error.value = null
  
  try {
    await Promise.all([
      fetchStatistics(),
      fetchActiveTasks(),
      fetchRecentTasks()
    ])
  } catch (e) {
    error.value = e.message
  } finally {
    isLoading.value = false
  }
}

/**
 * 格式化时间
 */
function formatTime(timestamp) {
  if (!timestamp) return '-'
  
  const date = new Date(timestamp)
  const now = new Date()
  const diff = now - date
  
  // 小于1分钟
  if (diff < 60000) {
    return '刚刚'
  }
  
  // 小于1小时
  if (diff < 3600000) {
    const mins = Math.floor(diff / 60000)
    return `${mins}分钟前`
  }
  
  // 小于24小时
  if (diff < 86400000) {
    const hours = Math.floor(diff / 3600000)
    return `${hours}小时前`
  }
  
  // 其他
  return date.toLocaleDateString('zh-CN', {
    month: 'numeric',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

/**
 * 获取状态颜色
 */
function getStatusColor(status) {
  const colors = {
    pending: '#ffc107',     // 黄色
    processing: '#2196f3',  // 蓝色
    completed: '#4caf50',   // 绿色
    failed: '#f44336'       // 红色
  }
  return colors[status] || '#999'
}

/**
 * 获取状态文本
 */
function getStatusText(status) {
  const texts = {
    pending: '等待中',
    processing: '处理中',
    completed: '已完成',
    failed: '失败'
  }
  return texts[status] || status
}

/**
 * 清除已完成任务
 */
async function clearCompleted() {
  try {
    await api.delete('/api/tasks?action=completed')
    await refresh()
  } catch (e) {
    console.error('Failed to clear tasks:', e)
  }
}

// 生命周期
onMounted(() => {
  refresh()
  
  if (props.autoRefresh) {
    refreshTimer = setInterval(refresh, props.refreshInterval)
  }
})

onUnmounted(() => {
  if (refreshTimer) {
    clearInterval(refreshTimer)
  }
})
</script>

<template>
  <div class="task-status-card">
    <!-- 错误提示 -->
    <div v-if="error" class="error-banner">
      ⚠️ {{ error }}
      <button @click="refresh">重试</button>
    </div>
    
    <!-- 统计卡片 -->
    <div class="stats-row">
      <div class="stat-card" @click="$emit('task-click', 'processing')">
        <div class="stat-icon processing">⚙️</div>
        <div class="stat-info">
          <div class="stat-value">{{ statistics.processing }}</div>
          <div class="stat-label">处理中</div>
        </div>
      </div>
      
      <div class="stat-card" @click="$emit('task-click', 'pending')">
        <div class="stat-icon pending">⏳</div>
        <div class="stat-info">
          <div class="stat-value">{{ statistics.pending }}</div>
          <div class="stat-label">等待中</div>
        </div>
      </div>
      
      <div class="stat-card completed" @click="$emit('task-click', 'completed')">
        <div class="stat-icon completed">✅</div>
        <div class="stat-info">
          <div class="stat-value">{{ statistics.completed }}</div>
          <div class="stat-label">已完成</div>
        </div>
      </div>
      
      <div class="stat-card failed" @click="$emit('task-click', 'failed')">
        <div class="stat-icon failed">❌</div>
        <div class="stat-info">
          <div class="stat-value">{{ statistics.failed }}</div>
          <div class="stat-label">失败</div>
        </div>
      </div>
    </div>
    
    <!-- 活跃任务列表 -->
    <div v-if="activeTasks.length > 0" class="active-tasks">
      <div class="section-header">
        <span class="pulse-dot"></span>
        <span>正在处理 ({{ activeTasks.length }})</span>
      </div>
      
      <div class="task-list">
        <div 
          v-for="task in activeTasks" 
          :key="task.id"
          class="task-item"
          @click="$emit('task-click', task)"
        >
          <div class="task-info">
            <div class="task-name">{{ task.name }}</div>
            <div class="task-message">{{ task.message }}</div>
          </div>
          <div class="task-progress">
            <div class="progress-bar">
              <div 
                class="progress-fill" 
                :style="{ width: task.progress + '%' }"
              ></div>
            </div>
            <span class="progress-text">{{ task.progress }}%</span>
          </div>
        </div>
      </div>
    </div>
    
    <!-- 最近任务 -->
    <div v-if="recentTasks.length > 0" class="recent-tasks">
      <div class="section-header">
        <span>最近任务</span>
        <button class="clear-btn" @click="clearCompleted" v-if="statistics.completed > 0">
          清除已完成
        </button>
      </div>
      
      <div class="task-list compact">
        <div 
          v-for="task in recentTasks" 
          :key="task.id"
          class="task-item compact"
          @click="$emit('task-click', task)"
        >
          <div class="task-status-dot" :style="{ background: getStatusColor(task.status) }"></div>
          <div class="task-name">{{ task.name }}</div>
          <div class="task-time">{{ formatTime(task.created_at) }}</div>
        </div>
      </div>
    </div>
    
    <!-- 加载状态 -->
    <div v-if="isLoading" class="loading-overlay">
      <div class="loading-spinner"></div>
    </div>
  </div>
</template>

<style scoped>
.task-status-card {
  position: relative;
  background: white;
  border-radius: 16px;
  padding: 16px;
  box-shadow: 0 4px 20px rgba(0,0,0,0.08);
}

.error-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px;
  background: #fff3f3;
  border-radius: 8px;
  margin-bottom: 16px;
  color: #d32f2f;
  font-size: 14px;
}

.error-banner button {
  padding: 4px 12px;
  background: #d32f2f;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

/* 统计行 */
.stats-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-bottom: 16px;
}

.stat-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  background: #f8f9fa;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.3s;
}

.stat-card:hover {
  background: #f0f0f0;
  transform: translateY(-2px);
}

.stat-icon {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 10px;
  font-size: 20px;
}

.stat-icon.processing {
  background: #e3f2fd;
}

.stat-icon.pending {
  background: #fff8e1;
}

.stat-icon.completed {
  background: #e8f5e9;
}

.stat-icon.failed {
  background: #ffebee;
}

.stat-value {
  font-size: 24px;
  font-weight: 600;
  color: #333;
}

.stat-label {
  font-size: 12px;
  color: #666;
}

/* 活跃任务 */
.active-tasks {
  margin-bottom: 16px;
}

.section-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 500;
  color: #333;
  margin-bottom: 12px;
}

.pulse-dot {
  width: 8px;
  height: 8px;
  background: #2196f3;
  border-radius: 50%;
  animation: pulse 1.5s infinite;
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0.5;
    transform: scale(1.2);
  }
}

.task-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.task-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  background: #f8f9fa;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s;
}

.task-item:hover {
  background: #f0f0f0;
}

.task-item.compact {
  padding: 8px 12px;
}

.task-name {
  flex: 1;
  font-size: 14px;
  color: #333;
}

.task-message {
  font-size: 12px;
  color: #666;
  margin-top: 2px;
}

.task-progress {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 100px;
}

.progress-bar {
  flex: 1;
  height: 6px;
  background: #e0e0e0;
  border-radius: 3px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
  border-radius: 3px;
  transition: width 0.3s;
}

.progress-text {
  font-size: 12px;
  color: #666;
  min-width: 36px;
  text-align: right;
}

/* 最近任务 */
.recent-tasks {
  border-top: 1px solid #f0f0f0;
  padding-top: 12px;
}

.recent-tasks .section-header {
  justify-content: space-between;
}

.clear-btn {
  padding: 4px 10px;
  background: transparent;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 12px;
  color: #666;
  cursor: pointer;
  transition: all 0.2s;
}

.clear-btn:hover {
  background: #f5f5f5;
  border-color: #ccc;
}

.task-item.compact {
  display: flex;
  gap: 8px;
  padding: 6px 12px;
}

.task-status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
  margin-top: 6px;
}

.task-time {
  font-size: 12px;
  color: #999;
}

/* 加载状态 */
.loading-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(255,255,255,0.8);
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 16px;
}

.loading-spinner {
  width: 30px;
  height: 30px;
  border: 3px solid #f0f0f0;
  border-top-color: #667eea;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
