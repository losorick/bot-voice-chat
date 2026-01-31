# Bot 语音沟通后端

## 概述

本后端用于对接阿里云百炼大模型 API，提供 RESTful 接口供前端调用。

## 快速开始

### 1. 安装依赖

```bash
cd /path/to/bot语音沟通/code/backend
pip install -r requirements.txt
```

### 2. 配置环境变量

在项目根目录创建 `.env` 文件：

```bash
# 阿里云百炼 API Key
export DASHSCOPE_API_KEY="sk-xxxxxxxx"
```

或者在运行前设置：

```bash
export DASHSCOPE_API_KEY="your_api_key_here"
```

### 3. 运行测试

```bash
python main.py --test
```

### 4. 启动 Web 服务

```bash
python main.py --server --port 5000
```

## 使用示例

### 基本对话

```python
from main import DashScopeClient

client = DashScopeClient()

response = client.chat([
    {"role": "user", "content": "你好，请介绍一下你自己"}
])

print(response['output']['text'])
```

### 多轮对话

```python
messages = [
    {"role": "user", "content": "今天天气怎么样？"},
    {"role": "assistant", "content": "我没有实时天气信息"},
    {"role": "user", "content": "那你能做什么？"}
]

response = client.chat(messages)
```

### 流式对话

```python
for chunk in client.chat_stream([
    {"role": "user", "content": "讲一个故事"}
]):
    print(chunk, end='', flush=True)
```

## API 接口

### 健康检查

```
GET /health
```

响应:
```json
{
    "status": "ok",
    "timestamp": "2026-01-30T22:00:00",
    "service": "dashscope-api"
}
```

### 对话接口

```
POST /api/chat
Content-Type: application/json

{
    "messages": [
        {"role": "system", "content": "你是一个助手"},
        {"role": "user", "content": "你好"}
    ],
    "model": "qwen-turbo",
    "temperature": 0.7,
    "max_tokens": 2000
}
```

### 模型列表

```
GET /api/models
```

响应:
```json
{
    "models": ["qwen-turbo", "qwen-plus", "qwen-max"],
    "default": "qwen-turbo"
}
```

## 支持的模型

| 模型名称 | 说明 | 适用场景 |
|---------|------|---------|
| qwen-turbo | 快速版 | 日常对话，响应速度快 |
| qwen-plus | 增强版 | 复杂任务，效果更好 |
| qwen-max | 最强版 | 高难度任务，质量最高 |
| text-embedding-v1 | 向量化 | 文本相似度计算 |

## 项目结构

```
backend/
├── main.py           # 主程序入口
├── requirements.txt  # 依赖列表
└── README.md         # 本文档
```

## 获取 API Key

1. 访问 [阿里云百炼控制台](https://bailian.console.aliyun.com/)
2. 注册/登录阿里云账号
3. 开通百炼服务
4. 创建 API Key

## 相关文档

- [阿里云百炼官方文档](https://help.aliyun.com/document_detail/2712193.html)
- [DashScope API 参考](https://help.aliyun.com/document_detail/2712196.html)

## 更新记录

- 2026-01-30: 初始版本，支持基本对话和向量化功能
