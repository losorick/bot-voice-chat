# Bot Voice Backend - 服务守护配置

本目录包含 bot语音沟通 后端服务的守护进程配置。

## 文件说明 (macOS)

- `com.bot.voice.backend.plist` - launchd 服务配置文件
- `.env` - 环境变量模板（需填入实际 API Key）

## 使用说明 (macOS)

### 1. 配置环境变量
编辑 `.env` 文件，填入实际的 API Key：
```bash
DASHSCOPE_API_KEY=your_actual_api_key_here
```

### 2. 加载服务配置
```bash
# 加载服务（注册到 launchd）
launchctl load ~/Library/LaunchAgents/com.bot.voice.backend.plist

# 或使用绝对路径
launchctl load /Users/mmcbot/Library/LaunchAgents/com.bot.voice.backend.plist
```

### 3. 启用服务（开机自启）
```bash
# 启用开机自启
launchctl enable ~/Library/LaunchAgents/com.bot.voice.backend.plist

# 或使用绝对路径
launchctl enable /Users/mmcbot/Library/LaunchAgents/com.bot.voice.backend.plist
```

### 4. 启动服务
```bash
launchctl start com.bot.voice.backend
```

### 5. 管理命令
```bash
# 查看服务状态
launchctl list | grep bot.voice

# 停止服务
launchctl stop com.bot.voice.backend

# 重启服务
launchctl stop com.bot.voice.backend && launchctl start com.bot.voice.backend

# 查看日志
tail -f /tmp/bot-voice-backend.log
tail -f /tmp/bot-voice-backend.error.log
```

### 6. 卸载服务
```bash
# 先停止
launchctl stop com.bot.voice.backend

# 卸载
launchctl unload ~/Library/LaunchAgents/com.bot.voice.backend.plist

# 禁用开机自启
launchctl disable ~/Library/LaunchAgents/com.bot.voice.backend.plist
```

### 7. 查看详细日志
```bash
# 使用 log show 查看系统日志
log show --predicate 'process == "Python"' --info --debug
```

## 服务配置说明

- **服务标签**: com.bot.voice.backend
- **工作目录**: `/Users/mmcbot/Documents/项目记录/bot语音沟通/code/backend`
- **启动命令**: `bot-voice-env/bin/python main.py --server --port 5002`
- **重启策略**: 崩溃后自动重启 (KeepAlive)
- **日志路径**:
  - 标准输出: `/tmp/bot-voice-backend.log`
  - 错误输出: `/tmp/bot-voice-backend.error.log`

## 注意事项

- 本配置使用 macOS launchd 服务
- 服务会在用户登录后自动启动（如果已启用）
- 确保 Python 虚拟环境路径正确
- API Key 敏感信息请勿提交到版本控制
- 日志文件过大时需要手动清理

## 故障排查

### 服务无法启动
```bash
# 检查日志
tail -f /tmp/bot-voice-backend.error.log

# 检查配置文件语法
plutil ~/Library/LaunchAgents/com.bot.voice.backend.plist
```

### 端口被占用
```bash
# 查看占用端口的进程
lsof -i :5002

# 修改端口（编辑 plist 文件中的 ProgramArguments）
```

### 重启服务
```bash
launchctl stop com.bot.voice.backend
sleep 2
launchctl start com.bot.voice.backend
```
