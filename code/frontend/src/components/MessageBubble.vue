<script setup>
import { computed } from 'vue'

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
</script>

<template>
  <div class="message" :class="{ 'message-user': isUser, 'message-assistant': !isUser }">
    <div class="avatar">
      {{ isUser ? '👤' : '🤖' }}
    </div>
    <div class="bubble">
      <div class="content">{{ content }}</div>
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

.message-user .avatar {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.bubble {
  padding: 12px 16px;
  border-radius: 16px;
  max-width: calc(100% - 48px);
}

.message-user .bubble {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border-bottom-right-radius: 4px;
}

.message-assistant .bubble {
  background: #f5f5f5;
  color: #333;
  border-bottom-left-radius: 4px;
}

.content {
  line-height: 1.5;
  word-wrap: break-word;
}

.time {
  font-size: 11px;
  opacity: 0.7;
  margin-top: 4px;
  text-align: right;
}
</style>
