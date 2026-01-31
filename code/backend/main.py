#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bot 语音沟通 - 阿里云百炼大模型测试后端

功能：
- 对接阿里云 DashScope API (百炼大模型)
- 支持环境变量读取 API Key
- 提供 RESTful API 接口
- 包含完整的测试用例

作者: Bot Voice Team
创建时间: 2026-01-30
"""

import os
import sys
import json
import re
import uuid
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from functools import wraps
from html import escape as html_escape

# ============================================================================
# 结构化日志配置
# ============================================================================

class JSONFormatter(logging.Formatter):
    """JSON 格式日志格式化器"""
    
    def format(self, record):
        log_obj = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'message': record.getMessage(),
            'logger': record.name,
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        if hasattr(record, 'request_id') and record.request_id:
            log_obj['request_id'] = record.request_id
        if hasattr(record, 'extra_data') and record.extra_data:
            log_obj['data'] = record.extra_data
        return json.dumps(log_obj)


def setup_logging():
    """初始化结构化日志配置"""
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # 清除已有处理器
    logger.handlers = []
    
    # 控制台处理器
    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())
    logger.addHandler(handler)
    
    return logger


def get_request_id():
    """生成请求 ID"""
    return str(uuid.uuid4())[:8]


def log_with_data(msg, level=logging.INFO, extra_data=None, request_id=None):
    """
    结构化日志输出
    
    Args:
        msg: 日志消息
        level: 日志级别
        extra_data: 附加数据 (dict)
        request_id: 请求 ID
    """
    logger = logging.getLogger()
    extra = {'request_id': request_id or getattr(logger, 'request_id', None)}
    if extra_data:
        extra['extra_data'] = extra_data
    
    logger.log(level, msg, extra=extra)

# 尝试导入 requests，如果不存在则提示安装
try:
    import requests
except ImportError:
    print("❌ 缺少依赖库，请运行: pip install requests")
    sys.exit(1)


# ============================================================================
# 安全防护模块
# ============================================================================

# SQL 注入检测正则（常见攻击模式）
SQL_INJECTION_PATTERNS = [
    r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|UNION|ALTER|CREATE|TRUNCATE)\b)",
    r"(--|;|/\*|\*/|@@|@)",
    r"(\bOR\b.*=.*\bOR\b)",
    r"(\bAND\b.*=.*\bAND\b)",
    r"['\"]",
    r"(EXEC(\s|\+)+(S|X)P\w+)",
    r"(0x[0-9a-fA-F]+)",
]

# XSS 攻击检测正则
XSS_PATTERNS = [
    r"<script.*?>.*?</script>",
    r"javascript:",
    r"on\w+\s*=",
    r"<iframe.*?>.*?</iframe>",
    r"<object.*?>.*?</object>",
    r"<embed.*?>",
    r"expression\s*\(",
    r"data:text/html",
    r"<svg.*?>.*?</svg>",
    r"onload|onerror|onmouseover",
]

# 危险字符黑名单（用于文件名、ID 等）
DANGEROUS_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f\x7f]')


class InputValidator:
    """输入验证器"""
    
    def __init__(self):
        self.sql_pattern = re.compile('|'.join(SQL_INJECTION_PATTERNS), re.IGNORECASE)
        self.xss_pattern = re.compile('|'.join(XSS_PATTERNS), re.IGNORECASE | re.DOTALL)
    
    def validate_string(self, value: Any, field_name: str = "field", 
                       max_length: int = 10000, allow_html: bool = False) -> str:
        """
        验证字符串输入
        
        Args:
            value: 输入值
            field_name: 字段名称（用于错误信息）
            max_length: 最大长度
            allow_html: 是否允许 HTML
            
        Returns:
            清理后的字符串
            
        Raises:
            ValueError: 验证失败
        """
        if value is None:
            raise ValueError(f"{field_name} 不能为空")
        
        if not isinstance(value, str):
            raise ValueError(f"{field_name} 必须是字符串类型")
        
        # 检查长度
        if len(value) > max_length:
            raise ValueError(f"{field_name} 长度不能超过 {max_length} 字符")
        
        if not value.strip():
            raise ValueError(f"{field_name} 不能为空或仅包含空白字符")
        
        # 检测 SQL 注入
        if self.sql_pattern.search(value):
            raise ValueError(f"{field_name} 包含非法字符或SQL注入特征")
        
        # 检测 XSS 攻击（除非允许 HTML）
        if not allow_html and self.xss_pattern.search(value):
            raise ValueError(f"{field_name} 包含潜在的XSS攻击特征")
        
        return value.strip()
    
    def sanitize_string(self, value: str, allow_html: bool = False) -> str:
        """
        清理字符串输入
        
        Args:
            value: 原始字符串
            allow_html: 是否允许 HTML
            
        Returns:
            清理后的字符串
        """
        if not isinstance(value, str):
            return str(value)
        
        # HTML 转义（除非允许 HTML）
        if not allow_html:
            value = html_escape(value)
        
        # 移除危险字符
        value = DANGEROUS_CHARS.sub('', value)
        
        # 规范化空白字符
        value = re.sub(r'\s+', ' ', value)
        
        return value.strip()
    
    def validate_conversation_id(self, conversation_id: str) -> str:
        """验证对话 ID 格式"""
        if not conversation_id:
            raise ValueError("conversation_id 不能为空")
        
        # 验证格式：只允许字母、数字、下划线、中划线
        if not re.match(r'^[a-zA-Z0-9_-]+$', conversation_id):
            raise ValueError("conversation_id 格式无效，只允许字母、数字、下划线和中划线")
        
        # 检测 SQL 注入
        if self.sql_pattern.search(conversation_id):
            raise ValueError("conversation_id 包含非法字符")
        
        return conversation_id
    
    def validate_role(self, role: str) -> str:
        """验证消息角色"""
        valid_roles = {'user', 'assistant', 'system'}
        role = role.lower().strip()
        
        if role not in valid_roles:
            raise ValueError(f"无效的角色: {role}，必须是: {', '.join(valid_roles)}")
        
        return role
    
    def validate_model(self, model: str) -> str:
        """验证模型名称"""
        if model not in Config.SUPPORTED_MODELS:
            raise ValueError(f"不支持的模型: {model}，支持的模型: {', '.join(Config.SUPPORTED_MODELS)}")
        return model
    
    def validate_temperature(self, temperature: Any) -> float:
        """验证温度参数"""
        try:
            temp = float(temperature)
        except (TypeError, ValueError):
            raise ValueError("temperature 必须是数字")
        
        if temp < 0 or temp > 2:
            raise ValueError("temperature 必须在 0-2 之间")
        
        return temp
    
    def validate_max_tokens(self, max_tokens: Any) -> int:
        """验证最大 token 数"""
        try:
            tokens = int(max_tokens)
        except (TypeError, ValueError):
            raise ValueError("max_tokens 必须是整数")
        
        if tokens < 1 or tokens > 128000:
            raise ValueError("max_tokens 必须在 1-128000 之间")
        
        return tokens
    
    def validate_message(self, message: Dict[str, Any]) -> Dict[str, str]:
        """
        验证消息格式
        
        Args:
            message: 消息字典
            
        Returns:
            验证后的消息字典
            
        Raises:
            ValueError: 验证失败
        """
        if not isinstance(message, dict):
            raise ValueError("消息必须是字典格式")
        
        if 'role' not in message:
            raise ValueError("消息必须包含 role 字段")
        
        if 'content' not in message:
            raise ValueError("消息必须包含 content 字段")
        
        role = self.validate_role(message['role'])
        content = self.validate_string(
            message['content'], 
            field_name="content", 
            max_length=50000
        )
        
        return {
            'role': role,
            'content': self.sanitize_string(content)
        }
    
    def validate_messages(self, messages: Any) -> List[Dict[str, str]]:
        """
        验证消息列表
        
        Args:
            messages: 消息列表
            
        Returns:
            验证后的消息列表
            
        Raises:
            ValueError: 验证失败
        """
        if not isinstance(messages, list):
            raise ValueError("messages 必须是列表格式")
        
        if len(messages) == 0:
            raise ValueError("messages 列表不能为空")
        
        if len(messages) > 100:
            raise ValueError("messages 列表不能超过 100 条")
        
        validated = []
        for i, msg in enumerate(messages):
            try:
                validated_msg = self.validate_message(msg)
                validated.append(validated_msg)
            except ValueError as e:
                raise ValueError(f"消息[{i}]验证失败: {e}")
        
        return validated


# 全局验证器实例
validator = InputValidator()


def validate_json_content_type(func):
    """验证 JSON 内容类型装饰器"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        if request.method in ['POST', 'PUT', 'PATCH']:
            content_type = request.content_type or ''
            if 'application/json' not in content_type:
                return jsonify({
                    'success': False,
                    'error': 'Content-Type 必须为 application/json',
                    'request_id': getattr(g, 'request_id', '')
                }), 400
        return func(*args, **kwargs)
    return wrapper


def safe_json_response(data: Any) -> Dict[str, Any]:
    """安全地构建 JSON 响应（自动转义敏感内容）"""
    def sanitize(obj):
        if isinstance(obj, str):
            return html_escape(obj)
        elif isinstance(obj, dict):
            return {k: sanitize(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [sanitize(item) for item in obj]
        else:
            return obj
    
    return sanitize(data)


# ============================================================================
# 配置管理
# ============================================================================

class Config:
    """配置管理类"""
    
    # 阿里云百炼 API 配置
    DASHSCOPE_API_KEY: str = os.environ.get('DASHSCOPE_API_KEY', '')
    DASHSCOPE_BASE_URL: str = 'https://dashscope.aliyuncs.com/api/v1'
    
    # 默认模型配置
    DEFAULT_MODEL: str = 'qwen-turbo'
    
    # 请求超时配置
    TIMEOUT: int = 30
    
    # 支持的模型列表
    SUPPORTED_MODELS: List[str] = [
        'qwen-turbo',
        'qwen-plus',
        'qwen-max',
        'qwen-max-0403',
        'qwen-max-0107',
        'text-embedding-v1',
        'text-embedding-v2'
    ]
    
    @classmethod
    def validate_config(cls) -> bool:
        """验证配置是否完整"""
        if not cls.DASHSCOPE_API_KEY:
            print("❌ 错误: 未设置 DASHSCOPE_API_KEY 环境变量")
            print("请在 .env 文件或 shell 配置中添加:")
            print('export DASHSCOPE_API_KEY="your_api_key_here"')
            return False
        return True


# ============================================================================
# DashScope API 客户端
# ============================================================================

class DashScopeClient:
    """阿里云百炼 API 客户端"""
    
    def __init__(self, api_key: Optional[str] = None, model: str = 'qwen-turbo'):
        """
        初始化 DashScope 客户端
        
        Args:
            api_key: 阿里云 API Key (默认从环境变量读取)
            model: 使用的模型名称
        """
        self.api_key = api_key or Config.DASHSCOPE_API_KEY
        self.model = model
        self.base_url = Config.DASHSCOPE_BASE_URL
        
        if not self.api_key:
            raise ValueError("API Key 未设置，请设置 DASHSCOPE_API_KEY 环境变量")
    
    def _get_headers(self) -> Dict[str, str]:
        """获取请求头"""
        return {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
            'X-DashScope-Async': 'disable'  # 同步调用模式
        }
    
    def _make_request(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        发起 HTTP 请求
        
        Args:
            endpoint: API 端点
            data: 请求数据
            
        Returns:
            API 响应 (JSON)
            
        Raises:
            RequestException: 请求失败时抛出异常
        """
        url = f"{self.base_url}{endpoint}"
        headers = self._get_headers()
        
        try:
            response = requests.post(
                url,
                headers=headers,
                json=data,
                timeout=Config.TIMEOUT
            )
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            print(f"❌ API 请求失败: {e}")
            raise
    
    def chat(self, messages: List[Dict[str, str]], 
             max_tokens: int = 2000,
             temperature: float = 0.7,
             **kwargs) -> Dict[str, Any]:
        """
        发起对话请求
        
        Args:
            messages: 对话消息列表，格式:
                [
                    {"role": "system", "content": "你是一个助手"},
                    {"role": "user", "content": "你好"}
                ]
            max_tokens: 最大生成 token 数
            temperature: 温度参数 (0-2)，越低越确定
            **kwargs: 其他参数
            
        Returns:
            对话响应
            
        Example:
            >>> client = DashScopeClient()
            >>> response = client.chat([
            ...     {"role": "user", "content": "你好，请介绍一下你自己"}
            ... ])
            >>> print(response['output']['text'])
        """
        endpoint = f'/services/aigc/text-generation/generation'
        
        payload = {
            'model': self.model,
            'input': {
                'messages': messages
            },
            'parameters': {
                'max_tokens': max_tokens,
                'temperature': temperature,
                **kwargs
            }
        }
        
        return self._make_request(endpoint, payload)
    
    def chat_stream(self, messages: List[Dict[str, str]], 
                    max_tokens: int = 2000,
                    temperature: float = 0.7) -> Any:
        """
        流式对话请求
        
        Args:
            messages: 对话消息列表
            max_tokens: 最大生成 token 数
            temperature: 温度参数
            
        Yields:
            流式响应片段
        """
        endpoint = f'/services/aigc/text-generation/generation'
        
        payload = {
            'model': self.model,
            'input': {
                'messages': messages
            },
            'parameters': {
                'max_tokens': max_tokens,
                'temperature': temperature,
                'incremental_output': True  # 开启流式输出
            }
        }
        
        url = f"{self.base_url}{endpoint}"
        headers = self._get_headers()
        headers['X-DashScope-Async'] = 'enable'  # 流式需要异步模式
        
        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=Config.TIMEOUT,
            stream=True
        )
        
        for line in response.iter_lines():
            if line:
                data = json.loads(line.decode('utf-8'))
                if data.get('output', {}).get('text'):
                    yield data['output']['text']
    
    def embedding(self, texts: List[str], model: str = 'text-embedding-v1') -> Dict[str, Any]:
        """
        文本向量化
        
        Args:
            texts: 文本列表
            model: 嵌入模型
            
        Returns:
            向量嵌入结果
        """
        endpoint = f'/services/embeddings/text-embedding/generation'
        
        # 阿里云向量化 API 使用 'texts' 字段
        payload = {
            'model': model,
            'input': {
                'texts': texts
            }
        }
        
        return self._make_request(endpoint, payload)


# ============================================================================
# Flask Web 服务
# ============================================================================

try:
    from flask import Flask, request, jsonify, g
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False
    print("⚠️ Flask 未安装，运行测试需要安装: pip install flask")

if FLASK_AVAILABLE:
    from flask import Flask, request, jsonify, g, Blueprint, redirect
    
    # 导入历史管理器
    from history_manager import get_history_manager
    
    # 初始化日志
    logger = setup_logging()
    
    # 创建 v1 蓝图
    v1_bp = Blueprint('v1', __name__)
    
    # 全局客户端实例
    _client: Optional[DashScopeClient] = None
    
    def get_client() -> DashScopeClient:
        """获取或创建客户端实例"""
        global _client
        if _client is None:
            _client = DashScopeClient()
        return _client
    
    @v1_bp.before_request
    def before_request():
        """请求前置处理：生成请求 ID"""
        g.request_id = get_request_id()
        logger.request_id = g.request_id
        log_with_data(f"Incoming request: {request.method} {request.path}", 
                     level=logging.INFO, 
                     request_id=g.request_id)
    
    @v1_bp.after_request
    def after_request(response):
        """请求后置处理：添加请求 ID 到响应头"""
        response.headers['X-Request-ID'] = getattr(g, 'request_id', '')
        return response
    
    @v1_bp.route('/health', methods=['GET'])
    def health_check():
        """健康检查接口"""
        log_with_data("Health check requested", request_id=g.request_id)
        return jsonify({
            'status': 'ok',
            'timestamp': datetime.now().isoformat(),
            'service': 'dashscope-api',
            'request_id': g.request_id
        })
    
    @v1_bp.route('/api/v1/chat', methods=['POST'])
    @validate_json_content_type
    def chat():
        """
        对话接口
        
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
        """
        request_id = g.request_id
        log_with_data("Chat request received", request_id=request_id, 
                     extra_data={'method': request.method, 'path': request.path})
        
        try:
            data = request.get_json()
            
            # 参数验证
            if not data or 'messages' not in data:
                log_with_data("Missing required parameter: messages", 
                             level=logging.WARNING, request_id=request_id)
                return jsonify({
                    'error': 'Missing required parameter: messages',
                    'request_id': request_id
                }), 400
            
            # ========== 输入验证开始 ==========
            # 验证并清理 messages
            try:
                messages = validator.validate_messages(data['messages'])
            except ValueError as e:
                log_with_data(f"Messages validation failed: {e}", 
                             level=logging.WARNING, request_id=request_id)
                return jsonify({
                    'error': f'消息验证失败: {e}',
                    'request_id': request_id
                }), 400
            
            # 验证 model 参数
            model = data.get('model', Config.DEFAULT_MODEL)
            try:
                model = validator.validate_model(model)
            except ValueError as e:
                return jsonify({
                    'error': str(e),
                    'request_id': request_id
                }), 400
            
            # 验证 temperature 参数
            temperature = data.get('temperature', 0.7)
            try:
                temperature = validator.validate_temperature(temperature)
            except ValueError as e:
                return jsonify({
                    'error': str(e),
                    'request_id': request_id
                }), 400
            
            # 验证 max_tokens 参数
            max_tokens = data.get('max_tokens', 2000)
            try:
                max_tokens = validator.validate_max_tokens(max_tokens)
            except ValueError as e:
                return jsonify({
                    'error': str(e),
                    'request_id': request_id
                }), 400
            
            # 验证 conversation_id（如果有）
            conversation_id = data.get('conversation_id')
            if conversation_id:
                try:
                    conversation_id = validator.validate_conversation_id(conversation_id)
                except ValueError as e:
                    return jsonify({
                        'error': str(e),
                        'request_id': request_id
                    }), 400
            # ========== 输入验证结束 ==========
            
            log_with_data("Calling DashScope API", request_id=request_id,
                         extra_data={'model': model, 'temperature': temperature})
            
            # 创建客户端并调用 API
            client = DashScopeClient(model=model)
            response = client.chat(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            # 提取响应内容
            output = response.get('output', {})
            assistant_text = output.get('text', '')
            usage = response.get('usage', {})
            input_tokens = usage.get('input_tokens', 0)
            output_tokens = usage.get('output_tokens', 0)
            
            # 保存到历史记录（如果有 conversation_id）
            if conversation_id:
                history_manager = get_history_manager()
                # 添加用户消息
                for msg in messages:
                    if msg['role'] == 'user':
                        history_manager.add_message(
                            conversation_id=conversation_id,
                            role='user',
                            content=msg['content'],
                            token_count=input_tokens
                        )
                        break
                # 添加助手回复
                history_manager.add_message(
                    conversation_id=conversation_id,
                    role='assistant',
                    content=assistant_text,
                    token_count=output_tokens
                )
            
            log_with_data("Chat response generated", request_id=request_id,
                         extra_data={'model': model, 'success': True})
            
            return jsonify({
                'success': True,
                'data': response,
                'conversation_id': conversation_id,
                'timestamp': datetime.now().isoformat(),
                'request_id': request_id
            })
            
        except Exception as e:
            log_with_data(f"Chat error: {str(e)}", 
                         level=logging.ERROR, request_id=request_id,
                         extra_data={'error_type': type(e).__name__})
            return jsonify({
                'success': False,
                'error': str(e),
                'request_id': request_id
            }), 500
    
    @v1_bp.route('/api/v1/models', methods=['GET'])
    def list_models():
        """获取支持的模型列表"""
        log_with_data("Models list requested", request_id=g.request_id)
        return jsonify({
            'models': Config.SUPPORTED_MODELS,
            'default': Config.DEFAULT_MODEL,
            'request_id': g.request_id
        })
    
    @v1_bp.route('/api/v1/config', methods=['GET'])
    def get_config():
        """获取当前配置（不包含敏感信息）"""
        log_with_data("Config requested", request_id=g.request_id)
        return jsonify({
            'api_key_configured': bool(Config.DASHSCOPE_API_KEY),
            'base_url': Config.DASHSCOPE_BASE_URL,
            'default_model': Config.DEFAULT_MODEL,
            'supported_models': Config.SUPPORTED_MODELS,
            'request_id': g.request_id
        })
    
    # ========== 对话历史管理 API ==========
    
    @v1_bp.route('/api/v1/conversations', methods=['GET'])
    def list_conversations():
        """
        获取对话列表
        
        GET /api/v1/conversations
        Query params:
            limit: 返回数量限制 (默认 20, 最大 100)
            offset: 偏移量 (默认 0)
        """
        # 验证 limit 参数
        try:
            limit = request.args.get('limit', 20, type=int)
            if limit < 1 or limit > 100:
                limit = 20  # 超出范围使用默认值
        except (TypeError, ValueError):
            limit = 20
        
        # 验证 offset 参数
        try:
            offset = request.args.get('offset', 0, type=int)
            if offset < 0:
                offset = 0
        except (TypeError, ValueError):
            offset = 0
        
        history_manager = get_history_manager()
        result = history_manager.get_conversations(limit=limit, offset=offset)
        
        return jsonify({
            'success': True,
            'data': result,
            'request_id': g.request_id
        })
    
    @v1_bp.route('/api/v1/conversations', methods=['POST'])
    @validate_json_content_type
    def create_conversation():
        """
        创建新对话
        
        POST /api/v1/conversations
        Body:
            title: 对话标题
            system_prompt: 系统提示词
        """
        data = request.get_json() or {}
        
        # 验证并清理 title（如果有）
        title = data.get('title')
        if title:
            try:
                title = validator.validate_string(
                    title, 
                    field_name='title', 
                    max_length=200
                )
            except ValueError as e:
                return jsonify({
                    'success': False,
                    'error': str(e),
                    'request_id': g.request_id
                }), 400
        
        # 验证并清理 system_prompt（如果有）
        system_prompt = data.get('system_prompt')
        if system_prompt:
            try:
                system_prompt = validator.validate_string(
                    system_prompt, 
                    field_name='system_prompt', 
                    max_length=10000
                )
            except ValueError as e:
                return jsonify({
                    'success': False,
                    'error': str(e),
                    'request_id': g.request_id
                }), 400
        
        history_manager = get_history_manager()
        conversation = history_manager.create_conversation(
            title=title,
            system_prompt=system_prompt
        )
        
        log_with_data("Conversation created", request_id=g.request_id,
                     extra_data={'conversation_id': conversation['id']})
        
        return jsonify({
            'success': True,
            'data': conversation,
            'request_id': g.request_id
        }), 201
    
    @v1_bp.route('/api/v1/conversations/<conversation_id>', methods=['GET'])
    def get_conversation(conversation_id: str):
        """
        获取对话详情
        
        GET /api/v1/conversations/<conversation_id>
        """
        # 验证 conversation_id 格式
        try:
            conversation_id = validator.validate_conversation_id(conversation_id)
        except ValueError as e:
            return jsonify({
                'success': False,
                'error': str(e),
                'request_id': g.request_id
            }), 400
        
        history_manager = get_history_manager()
        conversation = history_manager.get_conversation(conversation_id)
        
        if conversation is None:
            return jsonify({
                'success': False,
                'error': '对话不存在',
                'request_id': g.request_id
            }), 404
        
        return jsonify({
            'success': True,
            'data': conversation,
            'request_id': g.request_id
        })
    
    @v1_bp.route('/api/v1/conversations/<conversation_id>', methods=['DELETE'])
    def delete_conversation(conversation_id: str):
        """
        删除对话
        
        DELETE /api/v1/conversations/<conversation_id>
        """
        # 验证 conversation_id 格式
        try:
            conversation_id = validator.validate_conversation_id(conversation_id)
        except ValueError as e:
            return jsonify({
                'success': False,
                'error': str(e),
                'request_id': g.request_id
            }), 400
        
        history_manager = get_history_manager()
        success = history_manager.delete_conversation(conversation_id)
        
        if success:
            log_with_data("Conversation deleted", request_id=g.request_id,
                         extra_data={'conversation_id': conversation_id})
            return jsonify({
                'success': True,
                'message': '对话已删除',
                'request_id': g.request_id
            })
        else:
            return jsonify({
                'success': False,
                'error': '对话不存在',
                'request_id': g.request_id
            }), 404
    
    @v1_bp.route('/api/v1/conversations/<conversation_id>/messages', methods=['POST'])
    @validate_json_content_type
    def add_message(conversation_id: str):
        """
        添加消息到对话
        
        POST /api/v1/conversations/<conversation_id>/messages
        Body:
            role: 角色 (user/assistant/system)
            content: 消息内容
            token_count: Token 数量（可选）
        """
        # 验证 conversation_id 格式
        try:
            conversation_id = validator.validate_conversation_id(conversation_id)
        except ValueError as e:
            return jsonify({
                'success': False,
                'error': str(e),
                'request_id': g.request_id
            }), 400
        
        data = request.get_json()
        
        if not data or 'content' not in data:
            return jsonify({
                'success': False,
                'error': '缺少必需参数: content',
                'request_id': g.request_id
            }), 400
        
        # 验证并清理 content
        try:
            content = validator.validate_string(
                data['content'], 
                field_name='content',
                max_length=50000
            )
        except ValueError as e:
            return jsonify({
                'success': False,
                'error': str(e),
                'request_id': g.request_id
            }), 400
        
        # 验证 role
        role = data.get('role', 'user')
        try:
            role = validator.validate_role(role)
        except ValueError as e:
            return jsonify({
                'success': False,
                'error': str(e),
                'request_id': g.request_id
            }), 400
        
        token_count = data.get('token_count')
        
        history_manager = get_history_manager()
        message = history_manager.add_message(
            conversation_id=conversation_id,
            role=role,
            content=validator.sanitize_string(content),
            token_count=token_count
        )
        
        if message is None:
            return jsonify({
                'success': False,
                'error': '对话不存在',
                'request_id': g.request_id
            }), 404
        
        return jsonify({
            'success': True,
            'data': message,
            'request_id': g.request_id
        }), 201
    
    @v1_bp.route('/api/v1/conversations/<conversation_id>/export', methods=['GET'])
    def export_conversation(conversation_id: str):
        """
        导出对话内容
        
        GET /api/v1/conversations/<conversation_id>/export
        Query params:
            format: 导出格式 (json/text, 默认 json)
        """
        # 验证 conversation_id 格式
        try:
            conversation_id = validator.validate_conversation_id(conversation_id)
        except ValueError as e:
            return jsonify({
                'success': False,
                'error': str(e),
                'request_id': g.request_id
            }), 400
        
        # 验证 format 参数
        format_type = request.args.get('format', 'json')
        if format_type not in ['json', 'text']:
            return jsonify({
                'success': False,
                'error': 'format 参数无效，只支持 json 或 text',
                'request_id': g.request_id
            }), 400
        
        history_manager = get_history_manager()
        content = history_manager.export_conversation(
            conversation_id=conversation_id,
            format=format_type
        )
        
        if content is None:
            return jsonify({
                'success': False,
                'error': '对话不存在',
                'request_id': g.request_id
            }), 404
        
        # 根据格式返回响应
        if format_type == 'text':
            return content, 200, {'Content-Type': 'text/plain; charset=utf-8'}
        else:
            return jsonify({
                'success': True,
                'data': json.loads(content),
                'request_id': g.request_id
            })
    
    @v1_bp.route('/api/v1/history/stats', methods=['GET'])
    def get_history_stats():
        """
        获取历史统计信息
        
        GET /api/v1/history/stats
        """
        history_manager = get_history_manager()
        stats = history_manager.get_statistics()
        
        return jsonify({
            'success': True,
            'data': stats,
            'request_id': g.request_id
        })
    
    @v1_bp.route('/api/v1/history/clear', methods=['DELETE'])
    def clear_history():
        """
        清空所有对话历史
        
        DELETE /api/v1/history/clear
        """
        history_manager = get_history_manager()
        count = history_manager.clear_all()
        
        log_with_data("History cleared", request_id=g.request_id,
                     extra_data={'deleted_count': count})
        
        return jsonify({
            'success': True,
            'message': f'已清空 {count} 条对话记录',
            'deleted_count': count,
            'request_id': g.request_id
        })
    
    # 注册蓝图到 Flask 应用
    app = Flask(__name__)
    app.register_blueprint(v1_bp)
    
    # HTTPS 强制跳转中间件
    @app.before_request
    def force_https():
        """
        检测 HTTP 请求并重定向到 HTTPS
        
        生产环境默认启用，可通过环境变量 FORCE_HTTPS 控制:
        - FORCE_HTTPS=true  (默认) - 强制 HTTPS
        - FORCE_HTTPS=false - 允许 HTTP
        """
        force_https_env = os.environ.get('FORCE_HTTPS', 'true').lower() == 'true'
        
        if not force_https_env:
            return None
        
        # 检查是否是 HTTPS 请求（直接检查或通过代理头）
        if request.is_secure:
            return None
        
        # 检查 X-Forwarded-Proto 头（反向代理场景）
        forwarded_proto = request.headers.get('X-Forwarded-Proto', 'http')
        if forwarded_proto == 'https':
            return None
        
        # 构建 HTTPS URL 并重定向（301 永久重定向）
        url = request.url.replace('http://', 'https://', 1)
        return redirect(url, code=301)


# ============================================================================
# 测试模块
# ============================================================================

def test_basic_connection():
    """测试基本连接"""
    print("\n" + "="*60)
    print("🧪 测试 1: 基本连接测试")
    print("="*60)
    
    try:
        # 验证配置
        if not Config.validate_config():
            print("❌ 配置验证失败")
            return False
        
        # 创建客户端
        client = DashScopeClient()
        print(f"✅ 客户端创建成功")
        print(f"   模型: {client.model}")
        print(f"   Base URL: {client.base_url}")
        
        return True
        
    except Exception as e:
        print(f"❌ 连接测试失败: {e}")
        return False


def test_simple_chat():
    """测试简单对话"""
    print("\n" + "="*60)
    print("🧪 测试 2: 简单对话测试")
    print("="*60)
    
    try:
        client = DashScopeClient()
        
        messages = [
            {"role": "user", "content": "请用一句话介绍你自己"}
        ]
        
        print("📤 发送请求...")
        response = client.chat(messages, max_tokens=100)
        
        if response:
            print("✅ 请求成功!")
            print(f"\n📥 响应内容:")
            print("-" * 40)
            
            # 提取响应文本
            output = response.get('output', {})
            text = output.get('text', '无响应内容')
            print(text)
            print("-" * 40)
            
            # 打印 Token 使用情况
            usage = response.get('usage', {})
            if usage:
                print(f"\n📊 Token 使用情况:")
                print(f"   输入: {usage.get('input_tokens', 'N/A')}")
                print(f"   输出: {usage.get('output_tokens', 'N/A')}")
            
            return True
        else:
            print("❌ 无有效响应")
            return False
            
    except Exception as e:
        print(f"❌ 对话测试失败: {e}")
        return False


def test_multi_turn_chat():
    """测试多轮对话"""
    print("\n" + "="*60)
    print("🧪 测试 3: 多轮对话测试")
    print("="*60)
    
    try:
        client = DashScopeClient()
        
        # 多轮对话
        messages = [
            {"role": "user", "content": "今天天气怎么样？"},
            {"role": "assistant", "content": "作为一个 AI，我没有实时获取天气信息的能力。建议您查看手机天气应用获取准确信息。"},
            {"role": "user", "content": "那你推荐我穿什么衣服？"}
        ]
        
        print("📤 发送多轮对话请求...")
        response = client.chat(messages, max_tokens=200)
        
        if response:
            print("✅ 多轮对话成功!")
            print(f"\n📥 响应内容:")
            print("-" * 40)
            text = response.get('output', {}).get('text', '无响应内容')
            print(text)
            print("-" * 40)
            return True
        else:
            print("❌ 多轮对话失败")
            return False
            
    except Exception as e:
        print(f"❌ 多轮对话测试失败: {e}")
        return False


def test_embedding():
    """测试文本向量化"""
    print("\n" + "="*60)
    print("🧪 测试 4: 文本向量化测试")
    print("="*60)
    
    try:
        client = DashScopeClient()
        
        texts = [
            "你好，很高兴见到你",
            "今天天气真好",
            "人工智能技术发展迅速"
        ]
        
        print("📤 发送向量化请求...")
        response = client.embedding(texts)
        
        if response:
            print("✅ 向量化成功!")
            output = response.get('output', {})
            embeddings = output.get('embeddings', [])
            
            if embeddings:
                print(f"\n📊 向量信息:")
                print(f"   文本数量: {len(embeddings)}")
                print(f"   向量维度: {len(embeddings[0].get('embedding', []))}")
            
            return True
        else:
            print("❌ 向量化失败")
            return False
            
    except Exception as e:
        print(f"❌ 向量化测试失败: {e}")
        return False


def run_all_tests():
    """运行所有测试"""
    print("\n🚀 开始运行 DashScope API 测试")
    print("="*60)
    
    # 验证配置
    if not Config.validate_config():
        print("\n❌ 请先配置 DASHSCOPE_API_KEY 环境变量")
        print("示例:")
        print('export DASHSCOPE_API_KEY="sk-xxxxxxxx"')
        return
    
    results = []
    
    # 运行测试
    results.append(("基本连接", test_basic_connection()))
    
    if results[-1][1]:  # 只有基本连接成功才继续
        results.append(("简单对话", test_simple_chat()))
        results.append(("多轮对话", test_multi_turn_chat()))
        results.append(("文本向量化", test_embedding()))
    
    # 汇总结果
    print("\n" + "="*60)
    print("📊 测试结果汇总")
    print("="*60)
    
    passed = 0
    failed = 0
    
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"   {name}: {status}")
        if result:
            passed += 1
        else:
            failed += 1
    
    print("-" * 40)
    print(f"总计: {passed} 通过, {failed} 失败")
    print("="*60)
    
    if failed == 0:
        print("🎉 所有测试通过!")
    else:
        print("⚠️ 部分测试失败，请检查配置和网络")


# ============================================================================
# 主程序入口
# ============================================================================

def main():
    """主程序入口"""
    # 初始化结构化日志
    logger = setup_logging()
    logger.info("Application starting...")
    
    import argparse
    
    parser = argparse.ArgumentParser(
        description='阿里云百炼大模型测试后端',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 运行所有测试
  python main.py --test
  
  # 启动 Web 服务
  python main.py --server --port 8080
  
  # 单次对话测试
  python main.py --chat "你好"
        """
    )
    
    parser.add_argument('--test', action='store_true',
                        help='运行所有测试')
    parser.add_argument('--server', action='store_true',
                        help='启动 Flask Web 服务')
    parser.add_argument('--port', type=int, default=5000,
                        help='Web 服务端口 (默认: 5000)')
    parser.add_argument('--chat', type=str, metavar='MESSAGE',
                        help='发送单次对话请求')
    parser.add_argument('--model', type=str, default='qwen-turbo',
                        help='使用的模型 (默认: qwen-turbo)')
    
    args = parser.parse_args()
    
    # 验证配置
    if not Config.validate_config():
        sys.exit(1)
    
    if args.test:
        run_all_tests()
    elif args.chat:
        # 单次对话
        client = DashScopeClient(model=args.model)
        response = client.chat([
            {"role": "user", "content": args.chat}
        ])
        print("\n📥 响应:")
        print(response.get('output', {}).get('text', '无响应'))
    elif args.server:
        # 启动 Web 服务
        logger.info("Starting Flask server", extra={'extra_data': {'port': args.port}})
        print(f"\n🚀 启动 Web 服务...")
        print(f"   端口: {args.port}")
        print(f"   健康检查: http://localhost:{args.port}/api/v1/health")
        print(f"   对话接口: POST http://localhost:{args.port}/api/v1/chat")
        app.run(host='0.0.0.0', port=args.port, debug=True)
    else:
        # 默认运行测试
        run_all_tests()


if __name__ == '__main__':
    main()
