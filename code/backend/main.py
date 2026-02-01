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

# 加载 .env 文件
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

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

# 尝试导入 secrets 用于 CSRF token 生成
try:
    import secrets
except ImportError:
    # Python 3.6+ 内置 secrets 模块
    import random
    import string
    def secrets_token_hex(nbytes=None):
        """生成安全随机十六进制字符串"""
        if nbytes is None:
            nbytes = 32
        return ''.join(random.choices(string.hexdigits, k=nbytes * 2))
    secrets.token_hex = secrets_token_hex


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


# ============================================================================
# CSRF 防护模块
# ============================================================================

# CSRF token 存储（生产环境建议使用 Redis）
_csrf_tokens: Dict[str, float] = {}

# CSRF token 过期时间（秒）
CSRF_TOKEN_EXPIRY = 3600  # 1小时


class CSRFTokenManager:
    """CSRF Token 管理器"""
    
    @staticmethod
    def generate_token(session_id: str = "default") -> str:
        """
        生成 CSRF token
        
        Args:
            session_id: 会话 ID，用于区分不同来源的 token
            
        Returns:
            生成的 CSRF token
        """
        token = secrets.token_hex(32)
        # 存储 token 及其过期时间
        _csrf_tokens[token] = datetime.utcnow().timestamp() + CSRF_TOKEN_EXPIRY
        return token
    
    @staticmethod
    def validate_token(token: str) -> bool:
        """
        验证 CSRF token
        
        Args:
            token: 待验证的 token
            
        Returns:
            token 有效返回 True，否则返回 False
        """
        if not token:
            return False
        
        # 检查 token 是否在存储中且未过期
        expiry = _csrf_tokens.get(token)
        if expiry is None:
            return False
        
        # 检查是否过期
        if datetime.utcnow().timestamp() > expiry:
            # 清理过期 token
            del _csrf_tokens[token]
            return False
        
        return True
    
    @staticmethod
    def refresh_token(token: str) -> str:
        """
        刷新 token 的过期时间
        
        Args:
            token: 现有 token
            
        Returns:
            刷新后的 token（原 token 继续有效）
        """
        if token in _csrf_tokens:
            _csrf_tokens[token] = datetime.utcnow().timestamp() + CSRF_TOKEN_EXPIRY
            return token
        return None
    
    @staticmethod
    def cleanup_expired_tokens():
        """清理所有过期的 token"""
        current_time = datetime.utcnow().timestamp()
        expired_tokens = [token for token, expiry in _csrf_tokens.items() 
                         if current_time > expiry]
        for token in expired_tokens:
            del _csrf_tokens[token]
        return len(expired_tokens)


# CSRF 验证装饰器
def csrf_protected(f):
    """
    CSRF 保护装饰器
    
    用于保护敏感操作接口，需要在请求头或表单中提供有效的 CSRF token
    
    使用方式:
        @csrf_protected
        @app.route('/sensitive-action', methods=['POST'])
        def sensitive_action():
            ...
    
    Token 可以通过以下方式传递:
        - 请求头: X-CSRF-Token
        - 表单数据: csrf_token
        - JSON: csrf_token
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 获取 token（从请求头、表单或 JSON 中）
        token = None
        
        # 1. 优先从请求头获取
        token = request.headers.get('X-CSRF-Token')
        
        # 2. 如果请求头没有，从表单数据获取
        if not token and request.form:
            token = request.form.get('csrf_token')
        
        # 3. 如果表单没有，从 JSON 数据获取
        if not token and request.is_json:
            data = request.get_json(silent=True) or {}
            token = data.get('csrf_token')
        
        # 验证 token
        if not token:
            return jsonify({
                'success': False,
                'error': 'Missing CSRF token',
                'request_id': getattr(g, 'request_id', '')
            }), 400
        
        if not CSRFTokenManager.validate_token(token):
            return jsonify({
                'success': False,
                'error': 'Invalid or expired CSRF token',
                'request_id': getattr(g, 'request_id', '')
            }), 403
        
        # Token 验证通过，继续执行原函数
        return f(*args, **kwargs)
    
    return decorated_function


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
    from flask import Flask, request, jsonify, g, make_response, Blueprint, redirect, send_from_directory
    
    # 导入历史管理器
    from history_manager import get_history_manager
    
    # 导入上下文管理器
    from context_manager import get_context_manager
    
    # 导入任务管理器
    from task_manager import register_task_routes
    
    # 初始化日志
    logger = setup_logging()
    
    # 创建 v1 蓝图
    v1_bp = Blueprint('v1', __name__)
    
    # 临时音频文件目录
    TEMP_AUDIO_DIR = '/tmp/dashscope_asr_audio'
    os.makedirs(TEMP_AUDIO_DIR, exist_ok=True)
    
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
    
    # ========== 等待语音配置 ==========
    # 等待语音文件目录
    WAIT_AUDIO_DIR = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 
        'wait_audio'
    )
    
    # 类型映射文件路径
    WAIT_TYPES_JSON = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        '..', '..', 'wait_types.json'
    )
    
    def load_wait_types():
        """加载等待语音类型映射"""
        try:
            if os.path.exists(WAIT_TYPES_JSON):
                with open(WAIT_TYPES_JSON, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            log_with_data(f"Failed to load wait types: {e}", 
                         level=logging.WARNING, request_id=g.request_id)
        return {'confirm': [], 'waiting': [], 'completed': []}
    
    def get_wait_audio_files(audio_type: str = None):
        """获取等待语音文件列表
        
        Args:
            audio_type: 类型过滤 (confirm/waiting/completed)，None 则获取所有
        """
        if not os.path.exists(WAIT_AUDIO_DIR):
            return []
        
        # 如果指定了类型，从对应子目录获取
        if audio_type and audio_type in ['confirm', 'waiting', 'completed']:
            type_dir = os.path.join(WAIT_AUDIO_DIR, audio_type)
            if os.path.exists(type_dir):
                base_dir = type_dir
            else:
                # 子目录不存在时回退到主目录
                base_dir = WAIT_AUDIO_DIR
        else:
            base_dir = WAIT_AUDIO_DIR
        
        files = []
        for filename in os.listdir(base_dir):
            if filename.lower().endswith('.wav'):
                # 移除扩展名作为文本描述
                text = filename.rsplit('.', 1)[0]
                # 确定实际路径
                if base_dir != WAIT_AUDIO_DIR:
                    audio_url = f'/api/v1/wait-audio/file/{audio_type}/{filename}'
                else:
                    audio_url = f'/api/v1/wait-audio/file/{filename}'
                files.append({
                    'filename': filename,
                    'text': text,
                    'audioUrl': audio_url,
                    'type': audio_type or 'mixed'
                })
        return files
    
    def _get_random_wait_audio(audio_type: str = None):
        """随机获取一个等待语音
        
        Args:
            audio_type: 类型过滤 (confirm/waiting/completed)，None 则从所有类型随机选择
        """
        if audio_type and audio_type in ['confirm', 'waiting', 'completed']:
            # 从指定类型获取
            files = get_wait_audio_files(audio_type)
        else:
            # 从所有类型中先随机选择一个类型，再随机获取一个音频
            wait_types = load_wait_types()
            valid_types = [t for t in ['confirm', 'waiting', 'completed'] if wait_types.get(t)]
            if not valid_types:
                files = get_wait_audio_files()
            else:
                import random
                selected_type = random.choice(valid_types)
                files = get_wait_audio_files(selected_type)
        
        if not files:
            return None
        import random
        return random.choice(files)
    
    @v1_bp.route('/api/v1/wait-audio/file/<path:filename>', methods=['GET'])
    def serve_wait_audio(filename):
        """提供等待语音文件访问"""
        from urllib.parse import unquote
        from flask import send_file
        import mimetypes
        
        # URL 解码文件名
        filename = unquote(filename)
        
        # 安全检查：防止目录遍历
        if '..' in filename:
            return jsonify({
                'success': False,
                'error': '无效的文件名',
                'request_id': g.request_id
            }), 400
        
        # 检查是否在子目录中
        file_path = None
        if '/' in filename:
            parts = filename.split('/')
            if len(parts) == 2 and parts[0] in ['confirm', 'waiting', 'completed']:
                subdir = parts[0]
                sub_filename = parts[1]
                sub_dir = os.path.join(WAIT_AUDIO_DIR, subdir)
                if os.path.exists(sub_dir):
                    # 在目录中查找匹配的文件（忽略大小写）
                    for f in os.listdir(sub_dir):
                        if f.lower() == sub_filename.lower():
                            file_path = os.path.join(sub_dir, f)
                            break
        else:
            # 主目录查找
            if os.path.exists(WAIT_AUDIO_DIR):
                for f in os.listdir(WAIT_AUDIO_DIR):
                    if f.lower() == filename.lower():
                        file_path = os.path.join(WAIT_AUDIO_DIR, f)
                        break
        
        if file_path and os.path.exists(file_path):
            # 自动检测 MIME 类型
            mime_type, _ = mimetypes.guess_type(file_path)
            if mime_type is None:
                mime_type = 'audio/wav'
            return send_file(file_path, mimetype=mime_type)
        
        return 'File not found', 404
    
    @v1_bp.route('/api/v1/wait-audio/random', methods=['GET'])
    def get_random_wait_audio():
        """
        随机获取一个等待语音
        
        GET /api/wait-audio/random
        GET /api/wait-audio/random?type=confirm
        GET /api/wait-audio/random?type=waiting
        GET /api/wait-audio/random?type=completed
        
        Query params:
            type: 音频类型 (confirm/waiting/completed)，可选
            
        Returns:
            JSON 包含随机等待语音信息
            
        Example Response:
            {
                "code": 200,
                "data": {
                    "audioUrl": "/audio/wait/confirm/收到好的.wav",
                    "text": "收到好的",
                    "type": "confirm"
                }
            }
        """
        audio_type = request.args.get('type')
        
        # 验证 type 参数
        if audio_type and audio_type not in ['confirm', 'waiting', 'completed']:
            return jsonify({
                'code': 400,
                'error': '无效的 type 参数，支持的值: confirm, waiting, completed',
                'request_id': g.request_id
            }), 400
        
        log_with_data(f"Random wait audio requested, type={audio_type}", 
                     request_id=g.request_id)
        
        audio = _get_random_wait_audio(audio_type)
        
        if audio:
            return jsonify({
                'code': 200,
                'data': audio,
                'request_id': g.request_id
            })
        else:
            return jsonify({
                'code': 404,
                'error': '没有可用的等待语音文件',
                'request_id': g.request_id
            }), 404
    
    @v1_bp.route('/api/v1/wait-audio/list', methods=['GET'])
    def list_wait_audio():
        """
        获取所有等待语音文件列表
        
        GET /api/wait-audio/list
        
        Returns:
            JSON 包含所有等待语音文件列表
            
        Example Response:
            {
                "code": 200,
                "data": [
                    {"audioUrl": "/audio/wait/收到好的.wav", "text": "收到好的"},
                    {"audioUrl": "/audio/wait/请稍等.wav", "text": "请稍等"}
                ]
            }
        """
        log_with_data("Wait audio list requested", request_id=g.request_id)
        
        files = get_wait_audio_files()
        
        return jsonify({
            'code': 200,
            'data': files,
            'count': len(files),
            'request_id': g.request_id
        })
    
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
    
    @v1_bp.route('/api/v1/csrf-token', methods=['GET'])
    def get_csrf_token():
        """
        获取 CSRF token
        
        GET /api/v1/csrf-token
        
        Returns:
            JSON 包含 CSRF token
            
        Example Response:
            {
                "success": true,
                "csrf_token": "abc123...",
                "expires_in": 3600,
                "request_id": "xyz789"
            }
        """
        log_with_data("CSRF token requested", request_id=g.request_id)
        
        # 生成新的 CSRF token
        token = CSRFTokenManager.generate_token()
        
        # 定期清理过期 token（有一定概率执行）
        if secrets.randbelow(100) == 0:  # 1% 概率
            cleaned = CSRFTokenManager.cleanup_expired_tokens()
            if cleaned > 0:
                log_with_data(f"Cleaned {cleaned} expired CSRF tokens", 
                             request_id=g.request_id)
        
        return jsonify({
            'success': True,
            'csrf_token': token,
            'expires_in': CSRF_TOKEN_EXPIRY,
            'request_id': g.request_id
        })
    
    @v1_bp.route('/api/v1/chat', methods=['POST'])
    @v1_bp.route('/api/v1/chat/<path:api_key>', methods=['POST'])
    @validate_json_content_type
    def chat(api_key=None):
        """
        对话接口
        
        POST /api/chat
        POST /api/chat/<api_key>  (URL 后缀携带 API Key)
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
    
    @v1_bp.route('/api/v1/openclaw/chat', methods=['POST'])
    def openclaw_chat():
        """
        通过 OpenClaw 会话处理对话，并总结回复内容用于 TTS
        
        POST /api/v1/openclaw/chat
        Content-Type: application/json
        
        Parameters:
            message: 用户消息
            session_label: 会话标签 (默认: voice-chat)
            need_tts: 是否需要 TTS (默认: true)
            conversation_id: 对话 ID（可选，用于多轮对话上下文管理）
            system_prompt: 系统提示词（可选，创建新会话时使用）
        
        Returns:
            JSON 包含 AI 回复和 TTS 音频 URL
        """
        import subprocess
        import shlex
        import urllib.request
        from dashscope.audio.tts_v2 import SpeechSynthesizer, AudioFormat
        from dashscope.audio.tts_v2.speech_synthesizer import ResultCallback
        from io import BytesIO
        import wave
        
        try:
            data = request.get_json()
            if not data or 'message' not in data:
                return jsonify({
                    'success': False,
                    'error': '缺少消息内容',
                    'request_id': g.request_id
                }), 400
            
            message = data['message']
            session_label = data.get('session_label', 'voice-chat')
            need_tts = data.get('need_tts', True)
            
            # ========== 多轮对话上下文管理 ==========
            conversation_id = data.get('conversation_id')
            system_prompt = data.get('system_prompt')
            
            # 获取上下文管理器
            context_manager = get_context_manager()
            
            # 如果没有 conversation_id，创建一个新的
            if not conversation_id:
                conversation_id = session_label
                session_info = context_manager.create_session(
                    session_id=conversation_id,
                    system_prompt=system_prompt or "你是一个友好的语音助手，请用简洁的中文回复。"
                )
                log_with_data(f"Created new conversation session: {conversation_id}", 
                             request_id=g.request_id)
            else:
                # 获取现有会话
                session_info = context_manager.get_session(conversation_id)
                if not session_info:
                    # 会话不存在，创建新的
                    session_info = context_manager.create_session(
                        session_id=conversation_id,
                        system_prompt=system_prompt or "你是一个友好的语音助手，请用简洁的中文回复。"
                    )
                    log_with_data(f"Created new conversation for existing ID: {conversation_id}", 
                                 request_id=g.request_id)
            
            # 获取上下文历史消息
            context_messages = context_manager.get_messages(conversation_id)
            log_with_data(f"Context messages count: {len(context_messages)}", 
                         request_id=g.request_id)
            
            log_with_data(f"OpenClaw chat request: {message[:50]}...", 
                         request_id=g.request_id)
            
            # ========== 步骤 1: 获取 AI 回复 ==========
            # 构建包含上下文的提示词
            if context_messages:
                # 构造对话历史
                history_text = ""
                for msg in context_messages:
                    role_name = {'user': '用户', 'assistant': '助手', 'system': '系统'}.get(
                        msg['role'], msg['role']
                    )
                    history_text += f"{role_name}: {msg['content']}\n"
                
                task_prompt = f"""请处理以下语音对话请求，直接返回回复内容（不要添加任何解释或格式）：

=== 对话历史 ===
{history_text}
=== 当前消息 ===
用户说：{message}

请根据对话历史，用简短、友好的中文回复，保持对话连贯性。"""
            else:
                task_prompt = f"""请处理以下语音对话请求，直接返回回复内容（不要添加任何解释或格式）：

用户说：{message}

请用简短、友好的中文回复。"""
            
            cmd = [
                'openclaw', 'agent',
                '--message', task_prompt,
                '--session-id', session_label,
                '--local',
                '--timeout', '60'
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=90
            )
            
            if result.returncode != 0:
                return jsonify({
                    'success': False,
                    'error': result.stderr.strip() or 'OpenClaw 执行失败',
                    'request_id': g.request_id
                }), 500
            
            # 提取 AI 回复
            reply = result.stdout.strip()
            if reply.startswith('{') and '"reply"' in reply:
                import json as json_module
                try:
                    data = json_module.loads(reply)
                    reply = data.get('reply', reply)
                except:
                    pass
            
            log_with_data(f"AI reply: {reply[:100]}...", request_id=g.request_id)
            
            # ========== 保存用户消息和助手回复到上下文 ==========
            context_manager.add_message(conversation_id, 'user', message)
            context_manager.add_message(conversation_id, 'assistant', reply)
            
            response_data = {
                'success': True,
                'reply': reply,
                'conversation_id': conversation_id,
                'request_id': g.request_id
            }
            
            # ========== 步骤 2: Sub-agent 总结回复（用于 TTS）==========
            if need_tts:
                log_with_data("Starting sub-agent to summarize reply for TTS", 
                             request_id=g.request_id)
                
                summarize_prompt = f"""请用 1-2 句话总结以下内容，用于语音播报。要求：
1. 简洁明了
2. 保留核心意思
3. 口语化、自然

内容：
{reply}

只返回总结后的文字，不要其他内容。"""
                
                summarize_cmd = [
                    'openclaw', 'agent',
                    '--message', summarize_prompt,
                    '--session-id', f'{session_label}-tts-summary',
                    '--local',
                    '--timeout', '30'
                ]
                
                summary_result = subprocess.run(
                    summarize_cmd,
                    capture_output=True,
                    text=True,
                    timeout=45
                )
                
                if summary_result.returncode == 0:
                    summary = summary_result.stdout.strip()
                    # 清理 JSON 格式
                    if summary.startswith('{') and '"reply"' in summary:
                        try:
                            import json as json_module
                            data = json_module.loads(summary)
                            summary = data.get('reply', summary)
                        except:
                            pass
                    
                    # 如果总结太长或为空，使用原回复
                    if not summary or len(summary) > 200:
                        summary = reply[:200]
                    
                    log_with_data(f"TTS summary: {summary}", request_id=g.request_id)
                    
                    # ========== 步骤 3: 使用总结内容生成 TTS ==========
                    log_with_data("Generating TTS audio...", request_id=g.request_id)
                    
                    # 在应用上下文中生成 TTS
                    from flask import current_app
                    request_id_for_log = g.request_id  # 保存到局部变量
                    
                    with current_app.app_context():
                        # 收集音频数据
                        audio_chunks = []
                        
                        class AudioCallback(ResultCallback):
                            def on_open(self):
                                # 不调用 log_with_data，避免上下文问题
                                pass
                            
                            def on_complete(self):
                                pass
                            
                            def on_error(self, message: str):
                                pass
                            
                            def on_close(self):
                                pass
                            
                            def on_data(self, data: bytes) -> None:
                                audio_chunks.append(data)
                        
                        synthesizer = SpeechSynthesizer(
                            model='cosyvoice-v3-flash',
                            voice='longhuhu_v3',
                            format=AudioFormat.PCM_22050HZ_MONO_16BIT,
                            callback=AudioCallback()
                        )
                        
                        synthesizer.streaming_call(summary)
                        synthesizer.streaming_complete()
                        
                        audio_data = b''.join(audio_chunks)
                    
                    if len(audio_data) > 0:
                        # 创建 WAV 文件
                        wav_buffer = BytesIO()
                        with wave.open(wav_buffer, 'wb') as wav_file:
                            wav_file.setnchannels(1)
                            wav_file.setsampwidth(2)
                            wav_file.setframerate(22050)
                            wav_file.writeframes(audio_data)
                        
                        wav_data = wav_buffer.getvalue()
                        
                        response_data['tts_summary'] = summary
                        response_data['tts_audio'] = 'data:audio/wav;base64,' + \
                            __import__('base64').b64encode(wav_data).decode('ascii')
                    else:
                        log_with_data("TTS audio is empty", 
                                     level=logging.WARNING, request_id=g.request_id)
                else:
                    log_with_data(f"Summarize failed: {summary_result.stderr}", 
                                 level=logging.ERROR, request_id=g.request_id)
            
            return jsonify(response_data)
            
        except subprocess.TimeoutExpired:
            log_with_data("OpenClaw timeout", 
                         level=logging.ERROR, request_id=g.request_id)
            return jsonify({
                'success': False,
                'error': 'OpenClaw 会话超时',
                'request_id': g.request_id
            }), 504
        except Exception as e:
            log_with_data(f"OpenClaw chat error: {str(e)}", 
                         level=logging.ERROR, request_id=g.request_id)
            return jsonify({
                'success': False,
                'error': str(e),
                'request_id': g.request_id
            }), 500
    
    # ========== 多轮对话上下文管理 API ==========
    
    @v1_bp.route('/api/v1/context/sessions', methods=['GET'])
    def list_context_sessions():
        """
        获取所有上下文会话列表
        
        GET /api/v1/context/sessions
        
        Returns:
            JSON 包含所有会话列表
        """
        context_manager = get_context_manager()
        sessions = context_manager.get_all_sessions()
        stats = context_manager.get_statistics()
        
        return jsonify({
            'success': True,
            'data': {
                'sessions': sessions,
                'statistics': stats
            },
            'request_id': g.request_id
        })
    
    @v1_bp.route('/api/v1/context/sessions', methods=['POST'])
    @validate_json_content_type
    def create_context_session():
        """
        创建新上下文会话
        
        POST /api/v1/context/sessions
        Body:
            session_id: 会话 ID（可选）
            system_prompt: 系统提示词（可选）
        
        Returns:
            JSON 包含新创建的会话信息
        """
        data = request.get_json() or {}
        
        session_id = data.get('session_id')
        system_prompt = data.get('system_prompt')
        
        # 验证并清理 system_prompt（如果有）
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
        
        context_manager = get_context_manager()
        session = context_manager.create_session(
            session_id=session_id,
            system_prompt=system_prompt or "你是一个友好的语音助手，请用简洁的中文回复。"
        )
        
        log_with_data("Context session created", request_id=g.request_id,
                     extra_data={'session_id': session['id']})
        
        return jsonify({
            'success': True,
            'data': session,
            'request_id': g.request_id
        }), 201
    
    @v1_bp.route('/api/v1/context/sessions/<session_id>', methods=['GET'])
    def get_context_session(session_id: str):
        """
        获取会话上下文信息
        
        GET /api/v1/context/sessions/<session_id>
        
        Returns:
            JSON 包含会话信息和消息列表
        """
        # 验证 session_id 格式
        if not session_id or len(session_id) < 1:
            return jsonify({
                'success': False,
                'error': '无效的 session_id',
                'request_id': g.request_id
            }), 400
        
        context_manager = get_context_manager()
        session = context_manager.get_session(session_id)
        
        if session is None:
            return jsonify({
                'success': False,
                'error': '会话不存在',
                'request_id': g.request_id
            }), 404
        
        return jsonify({
            'success': True,
            'data': session,
            'request_id': g.request_id
        })
    
    @v1_bp.route('/api/v1/context/sessions/<session_id>/messages', methods=['GET'])
    def get_context_messages(session_id: str):
        """
        获取会话消息列表（API 格式）
        
        GET /api/v1/context/sessions/<session_id>/messages
        
        Returns:
            JSON 包含消息列表
        """
        # 验证 session_id 格式
        if not session_id or len(session_id) < 1:
            return jsonify({
                'success': False,
                'error': '无效的 session_id',
                'request_id': g.request_id
            }), 400
        
        context_manager = get_context_manager()
        messages = context_manager.get_messages(session_id)
        
        return jsonify({
            'success': True,
            'data': {
                'session_id': session_id,
                'messages': messages,
                'count': len(messages)
            },
            'request_id': g.request_id
        })
    
    @v1_bp.route('/api/v1/context/sessions/<session_id>', methods=['DELETE'])
    def delete_context_session(session_id: str):
        """
        删除会话上下文
        
        DELETE /api/v1/context/sessions/<session_id>
        
        Returns:
            JSON 包含操作结果
        """
        # 验证 session_id 格式
        if not session_id or len(session_id) < 1:
            return jsonify({
                'success': False,
                'error': '无效的 session_id',
                'request_id': g.request_id
            }), 400
        
        context_manager = get_context_manager()
        success = context_manager.delete_session(session_id)
        
        if success:
            log_with_data("Context session deleted", request_id=g.request_id,
                         extra_data={'session_id': session_id})
            return jsonify({
                'success': True,
                'message': '会话已删除',
                'request_id': g.request_id
            })
        else:
            return jsonify({
                'success': False,
                'error': '会话不存在',
                'request_id': g.request_id
            }), 404
    
    @v1_bp.route('/api/v1/context/sessions/<session_id>/messages', methods=['POST'])
    @validate_json_content_type
    def add_context_message(session_id: str):
        """
        添加消息到会话
        
        POST /api/v1/context/sessions/<session_id>/messages
        Body:
            role: 角色 (user/assistant/system)
            content: 消息内容
        
        Returns:
            JSON 包含添加的消息
        """
        # 验证 session_id 格式
        if not session_id or len(session_id) < 1:
            return jsonify({
                'success': False,
                'error': '无效的 session_id',
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
        
        context_manager = get_context_manager()
        message = context_manager.add_message(
            session_id=session_id,
            role=role,
            content=validator.sanitize_string(content)
        )
        
        if message is None:
            return jsonify({
                'success': False,
                'error': '会话不存在',
                'request_id': g.request_id
            }), 404
        
        return jsonify({
            'success': True,
            'data': message,
            'request_id': g.request_id
        }), 201
    
    @v1_bp.route('/api/v1/context/clear', methods=['DELETE'])
    def clear_all_context():
        """
        清空所有上下文会话
        
        DELETE /api/v1/context/clear
        
        Returns:
            JSON 包含清空的会话数量
        """
        context_manager = get_context_manager()
        count = context_manager.clear_all()
        
        log_with_data("All context sessions cleared", request_id=g.request_id,
                     extra_data={'deleted_count': count})
        
        return jsonify({
            'success': True,
            'message': f'已清空 {count} 个会话',
            'deleted_count': count,
            'request_id': g.request_id
        })
    
    @v1_bp.route('/api/v1/context/stats', methods=['GET'])
    def get_context_stats():
        """
        获取上下文统计信息
        
        GET /api/v1/context/stats
        
        Returns:
            JSON 包含统计信息
        """
        context_manager = get_context_manager()
        stats = context_manager.get_statistics()
        
        return jsonify({
            'success': True,
            'data': stats,
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
    @csrf_protected
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
    @csrf_protected
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
    @csrf_protected
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
    @csrf_protected
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
    
    @v1_bp.route('/api/v1/config/aliyun', methods=['GET'])
    def get_aliyun_config():
        """
        获取阿里云语音配置（公开信息）
        
        GET /api/v1/config/aliyun
        
        Returns:
            JSON 包含 App Key（如果配置了）
            注意：Token 需要动态获取，不通过此接口返回
        """
        app_key = os.environ.get('ALIYUN_APP_KEY', '')
        
        return jsonify({
            'success': True,
            'config': {
                'app_key': app_key,
                'has_config': bool(app_key),
                'tts_endpoint': 'https://nls-gateway.cn-shanghai.aliyuncs.com/rest/v1/tts',
                'asr_endpoint': 'wss://nls-gateway.cn-shanghai.aliyuncs.com/ws/v1'
            },
            'request_id': g.request_id
        })
    
    @v1_bp.route('/api/v1/asr/recognize', methods=['POST'])
    def asr_recognize():
        """
        语音识别接口（通过 DashScope Fun-ASR API）
        
        POST /api/v1/asr/recognize
        Content-Type: multipart/form-data
        
        Parameters:
            file: 音频文件 (wav, mp3, webm, etc.)
            model: 语音识别模型 (默认: fun-asr-mtl)
        
        Returns:
            JSON 包含识别结果
        """
        try:
            from http import HTTPStatus
            from dashscope.audio.asr import Transcription
            from dashscope import Files
            import urllib.request
            
            # 检查是否有音频文件
            if 'file' not in request.files:
                return jsonify({
                    'success': False,
                    'error': '缺少音频文件',
                    'request_id': g.request_id
                }), 400
            
            audio_file = request.files['file']
            
            # 获取模型名称
            model = request.form.get('model', 'fun-asr-mtl')
            
            # 保存临时文件
            import uuid
            filename = f'{uuid.uuid4()}.wav'
            temp_file_path = os.path.join(TEMP_AUDIO_DIR, filename)
            audio_file.save(temp_file_path)
            
            try:
                # 上传音频到 DashScope
                log_with_data(f"Uploading audio to DashScope...", request_id=g.request_id)
                
                upload_response = Files.upload(
                    file_path=temp_file_path,
                    purpose='transcription'
                )
                
                if upload_response.status_code != HTTPStatus.OK:
                    return jsonify({
                        'success': False,
                        'error': f'音频上传失败: {upload_response.message}',
                        'request_id': g.request_id
                    }), 500
                
                # 获取文件 URL（从列表中获取）
                list_response = Files.list(page=1, page_size=1)
                if list_response.status_code != HTTPStatus.OK or not list_response.output.get('files'):
                    return jsonify({
                        'success': False,
                        'error': '无法获取上传文件信息',
                        'request_id': g.request_id
                    }), 500
                
                file_url = list_response.output['files'][0]['url']
                log_with_data(f"Audio uploaded, URL: {file_url[:80]}...", request_id=g.request_id)
                
                # 调用 DashScope Fun-ASR API
                task_response = Transcription.async_call(
                    model=model,
                    file_urls=[file_url]
                )
                
                log_with_data(f"ASR task created: {task_response.output.task_id}", 
                             request_id=g.request_id)
                
                # 等待识别结果
                transcribe_response = Transcription.wait(task=task_response.output.task_id)
                
                log_with_data(f"ASR task status: {transcribe_response.output.get('task_status', 'UNKNOWN')}", 
                             request_id=g.request_id)
                
                if transcribe_response.status_code == HTTPStatus.OK:
                    task_status = transcribe_response.output.get('task_status', '')
                    if task_status != 'SUCCEEDED':
                        return jsonify({
                            'success': False,
                            'error': f'语音识别任务失败: {task_status}',
                            'request_id': g.request_id
                        }), 500
                    
                    # 获取转写结果 URL
                    results = transcribe_response.output.get('results', [])
                    if not results or 'transcription_url' not in results[0]:
                        return jsonify({
                            'success': False,
                            'error': '无法获取转写结果',
                            'request_id': g.request_id
                        }), 500
                    
                    result_url = results[0]['transcription_url']
                    
                    # 下载并解析结果
                    result_data = json.loads(urllib.request.urlopen(result_url).read().decode('utf-8'))
                    
                    # 提取识别文本
                    result_text = ''
                    if result_data.get('transcripts'):
                        result_text = result_data['transcripts'][0].get('text', '')
                    
                    log_with_data(f"ASR result: {result_text}", request_id=g.request_id)
                    
                    return jsonify({
                        'success': True,
                        'text': result_text,
                        'model': model,
                        'request_id': g.request_id
                    })
                else:
                    return jsonify({
                        'success': False,
                        'error': f'语音识别失败: {transcribe_response.message}',
                        'request_id': g.request_id
                    }), 500
                    
            finally:
                # 清理临时文件
                try:
                    os.remove(temp_file_path)
                except:
                    pass
                
        except KeyError as e:
            log_with_data(f"ASR KeyError: {str(e)}", 
                         level=logging.ERROR, request_id=g.request_id)
            return jsonify({
                'success': False,
                'error': f'语音识别响应格式错误: {str(e)}',
                'request_id': g.request_id
            }), 500
        except Exception as e:
            log_with_data(f"ASR error: {str(e)}", 
                         level=logging.ERROR, request_id=g.request_id)
            return jsonify({
                'success': False,
                'error': f'语音识别错误: {str(e)}',
                'request_id': g.request_id
            }), 500

    @v1_bp.route('/api/v1/tts/synthesize', methods=['POST'])
    def tts_synthesize():
        """
        语音合成接口（通过 DashScope TTS v2 API）
        
        POST /api/v1/tts/synthesize
        Content-Type: application/json
        
        Parameters:
            text: 要合成的文本
            voice: 音色 (默认: longanyang)
            format: 音频格式 (默认: pcm_22050hz_mono_16bit)
        
        Returns:
            音频流 (二进制)
        """
        try:
            from io import BytesIO
            from dashscope.audio.tts_v2 import SpeechSynthesizer, AudioFormat
            from dashscope.audio.tts_v2.speech_synthesizer import ResultCallback
            
            # 获取请求参数
            data = request.get_json()
            if not data or 'text' not in data:
                return jsonify({
                    'success': False,
                    'error': '缺少文本内容',
                    'request_id': g.request_id
                }), 400
            
            text = data['text']
            voice = data.get('voice', 'longanyang')
            
            log_with_data(f"TTS request: text={text[:50]}..., voice={voice}", 
                         request_id=g.request_id)
            
            # 收集所有音频数据
            audio_chunks = []
            
            # 定义回调类
            class AudioCallback(ResultCallback):
                def on_open(self):
                    log_with_data("TTS WebSocket connected", request_id=g.request_id)
                
                def on_complete(self):
                    log_with_data("TTS synthesis complete", request_id=g.request_id)
                
                def on_error(self, message: str):
                    log_with_data(f"TTS error: {message}", 
                                 level=logging.ERROR, request_id=g.request_id)
                
                def on_close(self):
                    log_with_data("TTS WebSocket closed", request_id=g.request_id)
                
                def on_data(self, data: bytes) -> None:
                    audio_chunks.append(data)
            
            # 创建合成器并合成语音 (使用 PCM 22050Hz mono 16bit)
            synthesizer = SpeechSynthesizer(
                model='cosyvoice-v3-flash',
                voice=voice,
                format=AudioFormat.PCM_22050HZ_MONO_16BIT,
                callback=AudioCallback()
            )
            
            # 流式发送文本
            synthesizer.streaming_call(text)
            synthesizer.streaming_complete()
            
            # 合并音频数据
            audio_data = b''.join(audio_chunks)
            
            log_with_data(f"TTS audio size: {len(audio_data)} bytes", 
                         request_id=g.request_id)
            
            if len(audio_data) == 0:
                return jsonify({
                    'success': False,
                    'error': '语音合成结果为空',
                    'request_id': g.request_id
                }), 500
            
            # 返回音频流 (添加 WAV 头)
            import wave
            import struct
            
            # 创建 WAV 文件
            wav_buffer = BytesIO()
            with wave.open(wav_buffer, 'wb') as wav_file:
                wav_file.setnchannels(1)  # mono
                wav_file.setsampwidth(2)  # 16-bit
                wav_file.setframerate(22050)
                wav_file.writeframes(audio_data)
            
            wav_data = wav_buffer.getvalue()
            
            response = make_response(wav_data)
            response.headers['Content-Type'] = 'audio/wav'
            response.headers['Content-Disposition'] = 'attachment; filename=speech.wav'
            response.headers['X-Request-ID'] = g.request_id
            
            return response
            
        except Exception as e:
            log_with_data(f"TTS error: {str(e)}", 
                         level=logging.ERROR, request_id=g.request_id)
            return jsonify({
                'success': False,
                'error': f'语音合成错误: {str(e)}',
                'request_id': g.request_id
            }), 500
    
    @v1_bp.route('/temp_audio/<filename>', methods=['GET'])
    def serve_temp_audio(filename):
        """提供临时音频文件访问"""
        from flask import send_file
        file_path = os.path.join(TEMP_AUDIO_DIR, filename)
        if os.path.exists(file_path):
            response = send_file(file_path, mimetype='audio/webm')
            # 访问后立即删除
            @response.call_on_close
            def cleanup():
                try:
                    os.remove(file_path)
                except:
                    pass
            return response
        return 'File not found', 404
    
    # 注册蓝图到 Flask 应用
    app = Flask(__name__)
    app.register_blueprint(v1_bp)
    
    # 注册任务管理路由
    register_task_routes(app)
    
    # 添加 CORS 支持
    @app.after_request
    def add_cors_headers(response):
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-API-Key, X-Request-ID'
        return response
    
    # HTTPS 强制跳转中间件
    @app.before_request
    def force_https():
        """
        检测 HTTP 请求并重定向到 HTTPS
        
        生产环境默认启用，可通过环境变量 FORCE_HTTPS 控制:
        - FORCE_HTTPS=true  (默认) - 强制 HTTPS
        - FORCE_HTTPS=false - 允许 HTTP
        """
        # 每次请求时动态读取环境变量
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
