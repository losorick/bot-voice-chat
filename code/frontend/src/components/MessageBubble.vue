<script setup>
import { computed } from 'vue'
import { marked } from 'marked'

const props = defineProps({
  role: {
    type: String,
    required: true,
    validator: (value) => ['user', 'assistant'].includes(value)
  },
  content: {
    type: String,
    required: true
  },
  timestamp: {
    type: Number,
    default: null
  }
})

const isUser = computed(() => props.role === 'user')

const formattedTime = computed(() => {
  if (!props.timestamp) return ''
  return new Date(props.timestamp).toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit'
  })
})

// 渲染 Markdown
const renderedContent = computed(() => {
  const content = props.content || ''
  // 配置 marked 简化输出
  marked.setOptions({
    breaks: true,  // 允许换行
    gfm: true      // GitHub 风格 Markdown
  })
  return marked.parse(content)
})
</script>

<template>
  <div class="message" :class="{ 'message-user': isUser, 'message-assistant': !isUser }">
    <div class="avatar">
      <span v-if="isUser">👤</span>
      <svg v-else viewBox="0 0 24 24" fill="currentColor" class="bot-avatar">
        <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 3c1.66 0 3 1.34 3 3s-1.34 3-3 3-3-1.34-3-3 1.34-3 3-3zm0 14.2c-2.5 0-4.71-1.28-6-3.22.03-1.99 4-3.08 6-3.08 1.99 0 5.97 1.09 6 3.08-1.29 1.94-3.5 3.22-6 3.22z"/>
      </svg>
    </div>
    <div class="bubble">
      <!-- 助手消息使用 Markdown 渲染 -->
      <div v-if="isUser" class="content">{{ content }}</div>
      <div v-else class="content markdown" v-html="renderedContent"></div>
      <div v-if="timestamp" class="time">{{ formattedTime }}</div>
    </div>
  </div>
</template>

<style scoped>
.message {
  display: flex;
  gap: 12px;
  padding: 12px;
  max-width: 80%;
}

.message-user {
  align-self: flex-end;
  flex-direction: row-reverse;
}

.message-assistant {
  align-self: flex-start;
}

.avatar {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  background: #f0f0f0;
  border-radius: 50%;
  flex-shrink: 0;
}

.bot-avatar {
  width: 24px;
  height: 24px;
  color: #666;
}

.message-user .avatar {
  background: #ff6b9d;
}

.bubble {
  padding: 12px 16px;
  border-radius: 16px;
  max-width: calc(100% - 48px);
}

.message-user .bubble {
  background: #ff6b9d;
  color: white;
  border-bottom-right-radius: 4px;
}

.message-assistant .bubble {
  background: #fffdd0;
  color: #333;
  border-bottom-left-radius: 4px;
}

.content {
  line-height: 1.5;
  word-wrap: break-word;
}

/* Markdown 样式 */
.markdown {
  font-size: 14px;
}

.markdown :deep(p) {
  margin: 0 0 8px 0;
}

.markdown :deep(p:last-child) {
  margin-bottom: 0;
}

.markdown :deep(code) {
  background: rgba(0, 0, 0, 0.08);
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 13px;
  font-family: 'SF Mono', Monaco, monospace;
}

.message-user .markdown :deep(code) {
  background: rgba(255, 255, 255, 0.2);
}

.markdown :deep(pre) {
  background: rgba(0, 0, 0, 0.05);
  padding: 12px;
  border-radius: 8px;
  overflow-x: auto;
  margin: 8px 0;
}

.message-user .markdown :deep(pre) {
  background: rgba(255, 255, 255, 0.1);
}

.markdown :deep(ul),
.markdown :deep(ol) {
  margin: 8px 0;
  padding-left: 20px;
}

.markdown :deep(strong) {
  font-weight: 600;
}

.markdown :deep(em) {
  font-style: italic;
}

.markdown :deep(a) {
  color: #ff6b9d;
  text-decoration: none;
}

.markdown :deep(a:hover) {
  text-decoration: underline;
}

/* 图片样式 */
.markdown :deep(img) {
  max-width: 100%;
  border-radius: 8px;
  border: 2px solid #ddd;
  margin: 8px 0;
}

.time {
  font-size: 11px;
  opacity: 0.7;
  margin-top: 4px;
  text-align: right;
}
</style>
