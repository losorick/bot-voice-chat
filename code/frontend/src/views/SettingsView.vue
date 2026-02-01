<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import BackendService from '../services/openclaw'

const router = useRouter()
const authStore = useAuthStore()

const apiKey = ref('')
const aliyunAppKey = ref('')
const aliyunToken = ref('')
const verificationStatus = ref('')
const isVerifying = ref(false)

async function saveSettings() {
  if (!apiKey.value.trim()) {
    alert('请输入 API Key')
    return
  }

  isVerifying.value = true
  verificationStatus.value = '验证中...'

  try {
    const result = await BackendService.verifyKey(apiKey.value.trim())
    
    if (result.success) {
      authStore.setApiKey(apiKey.value.trim())
      authStore.setVerified(Date.now().toString())
      
      // 保存阿里云配置
      if (aliyunAppKey.value.trim()) {
        localStorage.setItem('aliyun_appkey', aliyunAppKey.value.trim())
      }
      if (aliyunToken.value.trim()) {
        localStorage.setItem('aliyun_token', aliyunToken.value.trim())
      }
      
      verificationStatus.value = '✅ 验证成功！'
      setTimeout(() => {
        alert('设置已保存！')
        router.push('/')
      }, 500)
    } else {
      verificationStatus.value = `❌ ${result.error}`
    }
  } catch (error) {
    verificationStatus.value = `❌ 验证失败: ${error.message}`
  } finally {
    isVerifying.value = false
  }
}

function goBack() {
  router.push('/')
}

onMounted(() => {
  apiKey.value = authStore.apiKey || ''
  aliyunAppKey.value = localStorage.getItem('aliyun_appkey') || ''
  aliyunToken.value = localStorage.getItem('aliyun_token') || ''
})
</script>

<template>
  <div class="settings-view">
    <header class="settings-header">
      <button class="back-btn" @click="goBack">
        ← 返回
      </button>
      <h1>⚙️ 设置</h1>
    </header>

    <main class="settings-content">
      <section class="setting-section">
        <h2>🔐 API 认证</h2>
        <div class="form-group">
          <label>API Key</label>
          <input 
            v-model="apiKey"
            type="password"
            placeholder="请输入 API Key"
          />
          <span class="hint">从后端管理界面获取的 API Key</span>
          <div v-if="verificationStatus" class="verification-status">
            {{ verificationStatus }}
          </div>
        </div>
      </section>

      <section class="setting-section">
        <h2>🎤 阿里云语音配置</h2>
        <div class="form-group">
          <label>App Key</label>
          <input 
            v-model="aliyunAppKey"
            type="password"
            placeholder="阿里云语音识别 App Key"
          />
          <span class="hint">阿里云语音服务 App Key（用于语音识别和合成）</span>
        </div>
        <div class="form-group">
          <label>Token</label>
          <input 
            v-model="aliyunToken"
            type="password"
            placeholder="阿里云语音服务 Token"
          />
          <span class="hint">阿里云语音服务 Token（从阿里云控制台获取）</span>
        </div>
      </section>

      <div class="actions">
        <button 
          class="save-btn" 
          @click="saveSettings"
          :disabled="isVerifying"
        >
          {{ isVerifying ? '验证中...' : '保存设置' }}
        </button>
      </div>

      <div class="help-section">
        <h3>📖 API Key 获取方法</h3>
        <ol>
          <li>启动后端服务: <code>cd backend && python auth_api.py</code></li>
          <li>创建 API Key: <code>flask create-key</code></li>
          <li>复制生成的 Key 并在上方输入</li>
        </ol>
      </div>

      <div class="help-section">
        <h3>🎤 阿里云语音服务配置</h3>
        <ol>
          <li>访问 <a href="https://nls.console.aliyun.com/" target="_blank">阿里云智能语音服务</a></li>
          <li>创建语音识别（ASR）和语音合成（TTS）服务</li>
          <li>获取 App Key 和 Token</li>
          <li>在上方输入配置</li>
        </ol>
      </div>
    </main>
  </div>
</template>

<style scoped>
.settings-view {
  min-height: 100vh;
  background: #f5f5f5;
}

.settings-header {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px 24px;
  background: white;
  border-bottom: 1px solid #e0e0e0;
}

.back-btn {
  padding: 8px 16px;
  background: #f0f0f0;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
}

.settings-header h1 {
  font-size: 20px;
  margin: 0;
}

.settings-content {
  max-width: 600px;
  margin: 0 auto;
  padding: 24px;
}

.setting-section {
  background: white;
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 20px;
}

.setting-section h2 {
  font-size: 18px;
  margin: 0 0 16px;
  color: #333;
}

.form-group {
  margin-bottom: 16px;
}

.form-group:last-child {
  margin-bottom: 0;
}

.form-group label {
  display: block;
  margin-bottom: 8px;
  font-size: 14px;
  color: #666;
}

.form-group input,
.form-group select {
  width: 100%;
  padding: 12px;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  font-size: 16px;
  outline: none;
  transition: border-color 0.2s;
  box-sizing: border-box;
}

.form-group input:focus,
.form-group select:focus {
  border-color: #667eea;
}

.hint {
  display: block;
  margin-top: 6px;
  font-size: 12px;
  color: #999;
}

.verification-status {
  margin-top: 8px;
  padding: 8px 12px;
  border-radius: 6px;
  font-size: 14px;
}

.help-section {
  background: #e8f4fd;
  border-radius: 12px;
  padding: 20px;
  margin-top: 20px;
}

.help-section h3 {
  font-size: 16px;
  margin: 0 0 12px;
  color: #1a73e8;
}

.help-section ol {
  margin: 0;
  padding-left: 20px;
}

.help-section li {
  margin-bottom: 8px;
  color: #333;
}

.help-section code {
  background: rgba(0,0,0,0.1);
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 13px;
}

.actions {
  display: flex;
  justify-content: center;
}

.save-btn {
  padding: 14px 48px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 12px;
  font-size: 16px;
  cursor: pointer;
  transition: opacity 0.2s;
}

.save-btn:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.save-btn:hover:not(:disabled) {
  opacity: 0.9;
}
</style>
