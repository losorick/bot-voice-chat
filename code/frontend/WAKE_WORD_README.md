# 唤醒词检测功能说明

## 概述

本项目实现了基于 Picovoice Porcupine 的中文唤醒词检测功能。使用 "嘿助手" (hey_assistant) 作为唤醒词。

## 文件结构

```
code/frontend/
├── public/
│   └── wake-word/
│       ├── hey_assistant_zh.ppn    # 中文唤醒词模型文件
│       └── porcupine_params_zh.pv  # Porcupine 参数文件
├── src/
│   ├── composables/
│   │   └── useWakeWord.js          # 唤醒词检测 composable
│   └── components/
│       └── VoiceInput.vue          # 语音输入组件（已集成唤醒词）
└── package.json
```

## 使用方法

### 1. 启动开发服务器

```bash
cd code/frontend
npm run dev
```

### 2. 启用唤醒词模式

在聊天页面底部：
- 找到右侧的 💤 按钮（唤醒词模式切换）
- 点击按钮启用唤醒词模式（按钮变为 👂，显示"唤醒词模式"）
- 等待提示"等待唤醒词 '嘿助手'"

### 3. 说出唤醒词

说出 **"嘿助手"**，系统检测到唤醒词后会：
- 显示"唤醒词检测到！开始录音..."
- 自动开始录音（5秒后自动停止）
- 进行语音识别和发送

## 依赖安装

```bash
npm install @picovoice/porcupine-web @picovoice/web-voice-processor
```

## 唤醒词模型

当前使用开源的中文唤醒词 "嘿助手" (hey_assistant)。

### 更换唤醒词

1. 访问 [Picovoice Console](https://console.picovoice.ai/)
2. 创建自定义唤醒词或选择其他预训练模型
3. 下载 `.ppn` 文件（唤醒词）和 `.pv` 文件（参数）
4. 替换 `public/wake-word/` 目录下的文件
5. 修改 `VoiceInput.vue` 中的路径引用

## API

### useWakeWord()

```javascript
import { useWakeWord } from '../composables/useWakeWord'

const {
  wakeWordDetected,  // ref - 是否检测到唤醒词
  isListening,       // ref - 是否正在监听
  isInitialized,     // ref - 是否已初始化
  error,             // ref - 错误信息
  init,              // 初始化引擎
  start,             // 开始监听
  stop,              // 停止监听
  release,           // 释放资源
  onWakeWord         // 注册唤醒词回调
} = useWakeWord()

// 初始化
await init('/wake-word/hey_assistant_zh.ppn', '/wake-word/porcupine_params_zh.pv', {
  sensitivity: 0.6  // 灵敏度 (0-1)，越高越灵敏
})

// 开始监听
await start()

// 注册回调
onWakeWord(() => {
  console.log('唤醒词检测到！')
})
```

## 注意事项

1. **浏览器兼容性**：需要支持 Web Audio API 和麦克风权限
2. **HTTPS 要求**：麦克风访问通常需要 HTTPS 或 localhost
3. **性能考虑**：唤醒词检测会持续使用 CPU，建议在不需要时关闭
4. **唤醒词灵敏度**：可根据环境噪音调整灵敏度参数

## 故障排除

### 麦克风权限被拒绝
- 检查浏览器权限设置
- 确保使用 HTTPS 或 localhost

### 唤醒词检测不灵敏
- 降低环境噪音
- 靠近麦克风说话
- 调整 `sensitivity` 参数（提高值）

### 误检频繁
- 提高 `sensitivity` 参数（降低值）
- 减少背景噪音
