# Bot 语音沟通项目优化计划

> 创建时间: 2026-02-02  
> 项目路径: `~/Documents/项目记录/bot语音沟通`  
> 目标: 解决 4 个核心优化问题

---

## 📋 优化任务清单

| # | 问题 | 优先级 | 工作量 | 状态 |
|---|------|--------|--------|------|
| 1 | 后端服务自动停止问题 | P0 | 中等 | ⏳ 待分析 |
| 2 | 语音打断识别功能 | P0 | 中等 | ⏳ 待实现 |
| 3 | ASR 识别准确率优化 | P1 | 复杂 | ⏳ 待分析 |
| 4 | TTS 流式输出支持 | P0 | 复杂 | ⏳ 待实现 |

---

## 🎯 问题 1: 后端服务自动停止问题

### 1.1 根因分析

**现象描述:**
- 后端服务（5002/5005 端口）随机停止
- 无崩溃日志或错误信息
- 服务无响应但进程可能仍存在

**可能原因:**

#### A. 资源耗尽
```
├── 内存泄漏
│   ├── AudioContext 未正确关闭 (前端已实现 cleanup)
│   ├── 数据库连接未释放 (SQLite Storage)
│   └── WebSocket 连接泄漏
├── CPU 占用过高
│   └── 语音识别/合成阻塞主线程
└── 文件描述符耗尽
    └── 未关闭的文件句柄
```

#### B. 异常处理缺失
```
├── 未捕获的异常
│   ├── DashScope API 调用错误
│   └── ASR/TTS 流处理异常
├── 异步任务异常
│   └── background_task 未正确处理
└── 进程信号捕获
    └── 未处理 SIGHUP/SIGTERM
```

#### C. Flask 自身问题
```
├── 开发模式热重载问题
├── 请求超时设置
└── 线程池配置
```

### 1.2 解决方案

#### 方案 A: 增强服务稳定性 (基础)

**技术方案:**
1. 添加进程管理
   - 使用 `systemd` 或 `launchd` 管理服务
   - 配置自动重启策略
   - 添加健康检查端点

2. 增强日志记录
   - 添加结构化日志 (已有 JSONFormatter)
   - 增加请求追踪 ID
   - 记录资源使用情况

3. 资源监控
   - 内存使用监控
   - 线程/协程数量监控
   - API 调用耗时统计

**实现步骤:**

```python
# 步骤 1: 添加健康检查端点
@app.route('/health')
def health_check():
    return {
        'status': 'healthy',
        'uptime': get_uptime(),
        'memory': get_memory_usage(),
        'active_tasks': task_manager.get_active_count()
    }

# 步骤 2: 添加资源限制
MAX_CONCURRENT_REQUESTS = 10
REQUEST_TIMEOUT = 30  # 秒

# 步骤 3: 增强异常处理
@app.errorhandler(Exception)
def handle_exception(e):
    log_error(f"Unhandled exception: {e}")
    return {"error": "Internal server error"}, 500

# 步骤 4: 添加进程监控
def monitor_resources():
    while True:
        if memory_usage > threshold:
            log_warning("High memory usage", memory_usage)
        sleep(60)
```

#### 方案 B: 使用 Gunicorn/UWSGI (生产部署)

```bash
# 安装 gunicorn
pip install gunicorn

# 启动命令
gunicorn -w 4 -b 0.0.0.0:5005 --timeout 120 --keep-alive 5 main:app

# 配置 systemd 服务
[Unit]
Description=Bot Voice Backend Service
After=network.target

[Service]
Type=notify
User=mmcbot
WorkingDirectory=/path/to/backend
ExecStart=/path/to/venv/bin/gunicorn -w 4 -b 127.0.0.1:5005 --timeout 120 --keep-alive 5 main:app
Restart=always
RestartSec=10
Environment="PYTHONPATH=/path/to/backend"

[Install]
WantedBy=multi-user.target
```

### 1.3 具体实现步骤

| 步骤 | 内容 | 预估工时 |
|------|------|----------|
| 1.1 | 添加 `/health` 端点 | 1h |
| 1.2 | 添加内存/CPU 监控 | 2h |
| 1.3 | 配置 systemd 服务 | 1h |
| 1.4 | 添加请求超时和限流 | 2h |
| 1.5 | 测试和验证 | 2h |

**预估工作量: 中等 (8h)**

---

## 🎯 问题 2: 语音打断识别功能

### 2.1 根因分析

**当前实现分析:**

前端已有 `useSpeechInterrupt` 和 `useVAD`，但存在以下问题:

```
现有问题:
├── 打断检测阈值固定 (-50 dB)
├── 打断后未正确恢复对话状态
├── TTS 播放时无法实时检测用户语音
└── 打断时机判断不准确
```

**技术难点:**

1. **麦克风冲突**: TTS 播放时无法同时录音
   - 解决方案: 使用回声消除或虚拟设备

2. **状态同步**: 打断后需要通知后端停止生成
   - 需要 WebSocket 或轮询机制

3. **VAD 延迟**: 端点检测有延迟
   - 需要优化检测算法

### 2.2 解决方案

#### 方案 A: 客户端打断 (当前可行)

**技术方案:**

```javascript
// 1. TTS 播放时启用打断检测
async speak(text) {
  // 启动独立的打断检测麦克风流
  this.interruptStream = await navigator.mediaDevices.getUserMedia({ audio: true })
  
  // 使用独立的 AudioContext 进行检测
  this.interruptAnalyser = new AudioContext()
  const source = this.interruptAnalyser.createMediaStreamSource(this.interruptStream)
  source.connect(this.interruptAnalyser)
  
  // 开始检测
  this.detectInterrupt()
}

// 2. 检测到打断时
onInterruptDetected() {
  // 停止 TTS
  this.stop()
  
  // 通知后端取消生成 (如果支持)
  this.cancelBackendTask()
  
  // 切换到录音模式
  this.startRecording()
}

// 3. 后端支持取消
@app.route('/api/v1/chat/cancel', methods=['POST'])
def cancel_task():
    task_id = request.json.get('task_id')
    task_manager.cancel(task_id)
    return {"success": True}
```

#### 方案 B: 端云协同打断 (更优)

**架构设计:**

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   前端 VAD  │────▶│  后端取消   │────▶│  DashScope │
│  本地检测   │     │  任务管理   │     │  API 取消   │
└─────────────┘     └─────────────┘     └─────────────┘
```

**实现步骤:**

```python
# 后端: 任务管理器支持取消
class TaskManager:
    def __init__(self):
        self.tasks = {}
    
    def cancel(self, task_id):
        if task_id in self.tasks:
            task = self.tasks[task_id]
            task['cancelled'] = True
    
    def check_cancelled(self, task_id):
        return self.tasks.get(task_id, {}).get('cancelled', False)

# DashScope 流式响应时检查取消状态
def stream_chat(messages, task_id):
    for chunk in dashscope_stream:
        if task_manager.check_cancelled(task_id):
            return  # 提前退出
        yield chunk
```

### 2.3 具体实现步骤

| 步骤 | 内容 | 预估工时 |
|------|------|----------|
| 2.1 | 优化 `useSpeechInterrupt` 阈值自适应 | 2h |
| 2.2 | 实现 TTS 播放时打断检测 | 3h |
| 2.3 | 后端添加任务取消机制 | 3h |
| 2.4 | 前后端状态同步 | 2h |
| 2.5 | 测试打断体验 | 2h |

**预估工作量: 中等 (12h)**

---

## 🎯 问题 3: ASR 识别准确率优化

### 3.1 根因分析

**当前实现问题:**

```javascript
// 当前 ASR 配置
const asrConfig = {
  sampleRate: 16000,
  channelCount: 1,
  echoCancellation: true,
  noiseSuppression: true
}

// 问题:
├── 音频采样率可能不匹配 (DashScope 需要 16000)
├── 未使用端点检测 (VAD) 控制录音结束
├── WebM 格式可能不是最优
└── 没有自定义词汇表
```

**影响准确率的因素:**

```
识别准确率
├── 音频质量
│   ├── 采样率不匹配
│   ├── 背景噪音
│   ├── 麦克风距离
│   └── 说话音量
├── 语言模型
│   ├── 领域词汇缺失
│   ├── 同音字错误
│   └── 口语化表达
└── 网络延迟
    ├── 音频传输延迟
    └── API 响应时间
```

### 3.2 解决方案

#### 方案 A: 音频处理优化

**技术方案:**

```python
# 后端音频处理增强
def preprocess_audio(audio_data):
    # 1. 重采样到 16000Hz
    audio = resample(audio_data, target_sr=16000)
    
    # 2. 降噪处理
    audio = noise_reduction(audio)
    
    # 3. 音量标准化
    audio = normalize_volume(audio)
    
    # 4. 静音检测
    silence_removed = remove_silence(audio, threshold=-40dB)
    
    return silence_removed
```

#### 方案 B: DashScope Fun-ASR 参数优化

```python
# 使用更准确的模型参数
ASR_CONFIG = {
    'model': 'paraformer-v2',  # 或 fun-asr-mtl
    'input_type': 'audio/pcm',
    'sample_rate': 16000,
    # 启用标点符号
    'enable_punc': True,
    # 启用时间戳
    'enable_words': False,
    # 自定义热词
    'hotwords': 'Bot Voice助手 人工智能 机器学习'
}
```

#### 方案 C: 前端音频优化

```javascript
// 优化音频录制配置
const audioConfig = {
  echoCancellation: true,    // 开启回声消除
  noiseSuppression: true,    // 开启降噪
  autoGainControl: true,    // 自动增益控制
  sampleRate: 16000,        // 固定采样率
  channelCount: 1          // 单声道
}

// 使用更优的音频格式
const mimeType = MediaRecorder.isTypeSupported('audio/ogg;codecs=opus') 
  ? 'audio/ogg;codecs=opus'  // 更小文件
  : 'audio/webm;codecs=opus' // WebM 备选
```

### 3.3 具体实现步骤

| 步骤 | 内容 | 预估工时 |
|------|------|----------|
| 3.1 | 优化前端音频录制配置 | 2h |
| 3.2 | 后端添加音频预处理 | 3h |
| 3.3 | 配置 DashScope 优化参数 | 1h |
| 3.4 | 添加自定义热词支持 | 2h |
| 3.5 | 测试和调优 | 3h |

**预估工作量: 中等 (11h)**

---

## 🎯 问题 4: TTS 流式输出支持

### 4.1 根因分析

**当前实现问题:**

```javascript
// 当前 TTS 实现
async speak(text) {
  // 1. 发送完整文本到后端
  const response = await fetch('/api/v1/tts/synthesize', {
    body: JSON.stringify({ text })
  })
  
  // 2. 等待完整音频返回
  const blob = await response.blob()
  
  // 3. 播放整个音频
  const audio = new Audio(url)
  audio.play()
}

// 问题:
├── 首字节延迟高 (需要等待完整生成)
├── 无法实现边合成边播放
├── 用户打断响应慢
└── 内存占用高 (大音频文件)
```

**流式 vs 非流式对比:**

| 特性 | 非流式 | 流式 |
|------|--------|------|
| 首字节延迟 | 1-3s | <100ms |
| 打断响应 | >1s | <200ms |
| 内存占用 | 高 | 低 |
| 用户体验 | 卡顿 | 流畅 |
| 实现复杂度 | 低 | 高 |

### 4.2 解决方案

#### 方案 A: DashScope 流式 TTS

**技术方案:**

```python
# 后端流式 TTS 实现
from dashscope.audio.tts import SpeechSynthesizer
import asyncio

@app.route('/api/v1/tts/stream', methods=['POST'])
def tts_stream():
    text = request.json.get('text', '')
    voice = request.json.get('voice', 'longhuhu_v3')
    
    def generate():
        # 使用 DashScope 流式合成
        synthesizer = SpeechSynthesizer(
            model='cosyvoice-v3-flash',
            voice=voice,
            streaming=True
        )
        
        for chunk in synthesizer.stream_synthesize(text):
            yield chunk  # 音频分块
    
    return Response(
        generate(),
        mimetype='audio/pcm',
        headers={'X-Accel-Buffering': 'no'}
    )
```

#### 方案 B: 前端流式播放

```javascript
// 前端流式接收和播放
async playStreaming(text) {
  const response = await fetch('/api/v1/tts/stream', {
    method: 'POST',
    body: JSON.stringify({ text }),
    headers: { 'Accept': 'audio/pcm' }
  })
  
  // 使用 Web Audio API 流式播放
  const context = new AudioContext()
  const source = context.createBufferSource()
  
  // 分块接收音频数据
  const reader = response.body.getReader()
  const chunks = []
  
  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    chunks.push(value)
  }
  
  // 合并并播放
  const buffer = concatenateChunks(chunks)
  const audioBuffer = await context.decodeAudioData(buffer)
  source.buffer = audioBuffer
  source.connect(context.destination)
  source.start()
}
```

#### 方案 C: 更优的 Web Audio 播放

```javascript
// 使用 ScriptProcessor 或 AudioWorklet 实现真正的流式播放
class StreamingTTS {
  constructor() {
    this.context = new AudioContext()
    this.queue = []  // 音频块队列
    this.isPlaying = false
  }
  
  async start(text) {
    const response = await fetch('/api/v1/tts/stream', {
      method: 'POST',
      body: JSON.stringify({ text })
    })
    
    const reader = response.body.getReader()
    
    // 持续读取并添加到播放队列
    this.playLoop()
    
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      this.queue.push(value)
    }
  }
  
  async playLoop() {
    if (this.queue.length === 0) {
      await sleep(10)
      return
    }
    
    const chunk = this.queue.shift()
    await this.playChunk(chunk)
    this.playLoop()
  }
  
  async playChunk(chunk) {
    // 解码并播放音频块
    const buffer = await this.context.decodeAudioData(chunk)
    // ... 播放逻辑
  }
}
```

### 4.3 具体实现步骤

| 步骤 | 内容 | 预估工时 |
|------|------|----------|
| 4.1 | 后端实现 DashScope 流式 TTS | 4h |
| 4.2 | 前端流式接收音频 | 3h |
| 4.3 | 实现边合成边播放 | 4h |
| 4.4 | 打断时快速停止 | 2h |
| 4.5 | 测试和优化 | 3h |

**预估工作量: 复杂 (16h)**

---

## 📊 总工时估算

| 问题 | 预估工作量 | 优先级 |
|------|-----------|--------|
| 1. 后端服务稳定性 | 中等 (8h) | P0 |
| 2. 语音打断识别 | 中等 (12h) | P0 |
| 3. ASR 准确率优化 | 中等 (11h) | P1 |
| 4. TTS 流式输出 | 复杂 (16h) | P0 |
| **总计** | **~47h (约 6 个工作日)** | - |

---

## 🚀 执行顺序建议

### 第一阶段: P0 核心功能 (第 1-3 天)

1. **后端服务稳定性** - 确保服务不崩
2. **TTS 流式输出** - 提升用户体验

### 第二阶段: P0 体验优化 (第 4-5 天)

3. **语音打断识别** - 实现自然对话
4. **ASR 基础优化** - 音频参数调优

### 第三阶段: P1 精细化 (第 6 天)

5. **ASR 深度优化** - 降噪、热词
6. **测试和调优**

---

## 📝 附录

### A. 相关文件路径

```
bot语音沟通/
├── code/
│   ├── backend/
│   │   ├── main.py          # 主服务 (Flask)
│   │   ├── sqlite_storage.py # 数据存储
│   │   └── context_manager.py
│   └── frontend/
│       ├── src/
│       │   ├── services/
│       │   │   ├── asr.js      # 语音识别服务
│       │   │   ├── tts.js      # 语音合成服务
│       │   │   └── openclaw.js
│       │   ├── composables/
│       │   │   ├── useSpeechInterrupt.js
│       │   │   └── useVAD.js
│       │   └── views/
│       │       └── ChatView.vue
│       └── ...
└── OPTIMIZATION_PLAN.md   # 本文档
```

### B. 技术参考

- [DashScope 语音合成文档](https://help.aliyun.com/zh/dashscope/)
- [Web Audio API](https://developer.mozilla.org/en-US/docs/Web/API/Web_Audio_API)
- [MediaRecorder API](https://developer.mozilla.org/en-US/docs/Web/API/MediaRecorder)

---

*文档生成时间: 2026-02-02*
