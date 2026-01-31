#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API Key 认证管理系统 + 任务队列管理
用于管理前端访问后端的 API Keys 和任务状态
"""

import os
import hashlib
import secrets
import json
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, request, jsonify
from flask_cors import CORS
import jwt
import uuid

# 导入任务管理模块
from task_manager import TaskManager, register_task_routes, ConversationTask

app = Flask(__name__)
CORS(app)

# ============================================================================
# JWT 配置
# ============================================================================

class JWTConfig:
    """JWT 配置类"""
    
    # 密钥（从环境变量读取或使用默认值）
    SECRET_KEY = os.environ.get('JWT_SECRET_KEY', secrets.token_urlsafe(32))
    
    # Access Token 过期时间（默认 30 分钟，可配置）
    ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get('JWT_ACCESS_TOKEN_EXPIRE_MINUTES', 30))
    
    # Refresh Token 过期时间（默认 7 天，可配置）
    REFRESH_TOKEN_EXPIRE_DAYS = int(os.environ.get('JWT_REFRESH_TOKEN_EXPIRE_DAYS', 7))
    
    # Token 算法
    ALGORITHM = 'HS256'


def get_token_expire_times():
    """获取 token 过期时间配置"""
    return {
        'access_token_expire_minutes': JWTConfig.ACCESS_TOKEN_EXPIRE_MINUTES,
        'refresh_token_expire_days': JWTConfig.REFRESH_TOKEN_EXPIRE_DAYS
    }


def generate_tokens(api_key_id, key_name):
    """生成 access token 和 refresh token"""
    
    now = datetime.utcnow()
    
    # Access Token payload
    access_payload = {
        'sub': api_key_id,
        'name': key_name,
        'type': 'access',
        'jti': str(uuid.uuid4()),
        'iat': now,
        'exp': now + timedelta(minutes=JWTConfig.ACCESS_TOKEN_EXPIRE_MINUTES)
    }
    
    # Refresh Token payload
    refresh_payload = {
        'sub': api_key_id,
        'type': 'refresh',
        'jti': str(uuid.uuid4()),
        'iat': now,
        'exp': now + timedelta(days=JWTConfig.REFRESH_TOKEN_EXPIRE_DAYS)
    }
    
    access_token = jwt.encode(
        access_payload,
        JWTConfig.SECRET_KEY,
        algorithm=JWTConfig.ALGORITHM
    )
    
    refresh_token = jwt.encode(
        refresh_payload,
        JWTConfig.SECRET_KEY,
        algorithm=JWTConfig.ALGORITHM
    )
    
    return {
        'access_token': access_token,
        'refresh_token': refresh_token,
        'token_type': 'Bearer',
        'expires_in': JWTConfig.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        'expires_at': access_payload['exp'].isoformat()
    }


def verify_token(token, token_type='access'):
    """验证 token 并返回 payload"""
    try:
        payload = jwt.decode(
            token,
            JWTConfig.SECRET_KEY,
            algorithms=[JWTConfig.ALGORITHM]
        )
        
        # 验证 token 类型
        if token_type == 'access' and payload.get('type') != 'access':
            return {'valid': False, 'error': 'Invalid token type'}
        elif token_type == 'refresh' and payload.get('type') != 'refresh':
            return {'valid': False, 'error': 'Invalid token type'}
        
        return {
            'valid': True,
            'payload': payload,
            'api_key_id': payload.get('sub'),
            'key_name': payload.get('name')
        }
    
    except jwt.ExpiredSignatureError:
        return {'valid': False, 'error': 'Token has expired'}
    except jwt.InvalidTokenError as e:
        return {'valid': False, 'error': f'Invalid token: {str(e)}'}


def refresh_access_token(refresh_token):
    """使用 refresh token 获取新的 access token"""
    result = verify_token(refresh_token, 'refresh')
    
    if not result['valid']:
        return result
    
    # 获取 key 名称
    keys = load_keys()
    api_key_id = result['api_key_id']
    key_name = keys.get(api_key_id, {}).get('name', '')
    
    # 生成新的 token 对
    tokens = generate_tokens(api_key_id, key_name)
    
    return {
        'valid': True,
        **tokens
    }


# ============================================================================
# Token 存储（简单的内存存储，生产环境建议使用 Redis）
# ============================================================================

_revoked_tokens = set()


def revoke_token(jti):
    """撤销 token"""
    _revoked_tokens.add(jti)


def is_token_revoked(jti):
    """检查 token 是否已撤销"""
    return jti in _revoked_tokens


# 注册任务管理路由
register_task_routes(app)

# API Keys 存储文件
KEYS_FILE = 'api_keys.json'

def load_keys():
    """加载 API Keys"""
    if os.path.exists(KEYS_FILE):
        with open(KEYS_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_keys(keys):
    """保存 API Keys"""
    with open(KEYS_FILE, 'w') as f:
        json.dump(keys, f, indent=2, ensure_ascii=False)

def hash_key(key):
    """哈希 API Key（只保存哈希值）"""
    return hashlib.sha256(key.encode()).hexdigest()

def generate_api_key():
    """生成新的 API Key"""
    return 'bk_' + secrets.token_urlsafe(32)

# ============================================================================
# API Key 管理接口
# ============================================================================

@app.route('/api/keys', methods=['GET'])
def list_keys():
    """列出所有 API Keys（不返回完整 key）"""
    keys = load_keys()
    
    result = []
    for key_id, key_data in keys.items():
        result.append({
            'id': key_id,
            'name': key_data.get('name', ''),
            'created_at': key_data.get('created_at', ''),
            'last_used': key_data.get('last_used', ''),
            'is_active': key_data.get('is_active', True),
            'key_prefix': key_data['key'][:10] + '...' if len(key_data['key']) > 10 else key_data['key']
        })
    
    return jsonify({
        'success': True,
        'keys': result
    })

@app.route('/api/keys', methods=['POST'])
def create_key():
    """创建新的 API Key"""
    data = request.get_json()
    name = data.get('name', '').strip()
    
    if not name:
        return jsonify({'success': False, 'error': '名称不能为空'}), 400
    
    keys = load_keys()
    
    # 生成新的 key
    new_key = generate_api_key()
    key_id = datetime.now().strftime('%Y%m%d%H%M%S')
    
    keys[key_id] = {
        'key': new_key,
        'name': name,
        'created_at': datetime.now().isoformat(),
        'last_used': None,
        'is_active': True
    }
    
    save_keys(keys)
    
    return jsonify({
        'success': True,
        'key': {
            'id': key_id,
            'name': name,
            'key': new_key,  # 只在创建时返回完整 key
            'created_at': keys[key_id]['created_at']
        }
    })

@app.route('/api/keys/<key_id>', methods=['DELETE'])
def delete_key(key_id):
    """删除 API Key"""
    keys = load_keys()
    
    if key_id not in keys:
        return jsonify({'success': False, 'error': 'Key 不存在'}), 404
    
    del keys[key_id]
    save_keys(keys)
    
    return jsonify({'success': True})

@app.route('/api/keys/<key_id>/toggle', methods=['POST'])
def toggle_key(key_id):
    """启用/禁用 API Key"""
    keys = load_keys()
    
    if key_id not in keys:
        return jsonify({'success': False, 'error': 'Key 不存在'}), 404
    
    keys[key_id]['is_active'] = not keys[key_id]['is_active']
    save_keys(keys)
    
    return jsonify({
        'success': True,
        'is_active': keys[key_id]['is_active']
    })

# ============================================================================
# Token 刷新接口
# ============================================================================

@app.route('/api/auth/token', methods=['POST'])
def get_token():
    """获取 Token（使用 API Key 换取 JWT Token）"""
    data = request.get_json()
    
    api_key_value = data.get('api_key')
    
    if not api_key_value:
        return jsonify({
            'success': False,
            'error': 'Missing API Key',
            'message': '请提供 api_key 参数'
        }), 401
    
    # 验证 API Key
    keys = load_keys()
    key_id = None
    key_name = ''
    
    for kid, kdata in keys.items():
        if kdata['key'] == api_key_value:
            key_id = kid
            key_name = kdata.get('name', '')
            break
    
    if not key_id:
        return jsonify({
            'success': False,
            'error': 'Invalid API Key',
            'message': 'API Key 无效'
        }), 401
    
    key_data = keys[key_id]
    
    if not key_data.get('is_active', True):
        return jsonify({
            'success': False,
            'error': 'API Key Disabled',
            'message': 'API Key 已被禁用'
        }), 403
    
    # 生成 JWT Token 对
    tokens = generate_tokens(key_id, key_name)
    
    # 更新最后使用时间
    key_data['last_used'] = datetime.now().isoformat()
    save_keys(keys)
    
    return jsonify({
        'success': True,
        **tokens
    })


@app.route('/api/auth/refresh', methods=['POST'])
def refresh_token():
    """刷新 Access Token"""
    data = request.get_json()
    refresh_token_value = data.get('refresh_token')
    
    if not refresh_token_value:
        return jsonify({
            'success': False,
            'error': 'Missing refresh_token',
            'message': '请提供 refresh_token 参数'
        }), 400
    
    result = refresh_access_token(refresh_token_value)
    
    if not result.get('valid'):
        return jsonify({
            'success': False,
            'error': result.get('error', 'Invalid refresh token')
        }), 401
    
    return jsonify({
        'success': True,
        'access_token': result['access_token'],
        'token_type': 'Bearer',
        'expires_in': result['expires_in'],
        'expires_at': result['expires_at']
    })


@app.route('/api/auth/config', methods=['GET'])
def auth_config():
    """获取认证配置（公开信息）"""
    expire_config = get_token_expire_times()
    
    return jsonify({
        'success': True,
        'config': {
            'token_type': 'Bearer',
            **expire_config
        }
    })


# ============================================================================
# JWT Token 验证中间件
# ============================================================================

def require_jwt_token(f):
    """JWT Token 验证装饰器"""
    @wraps(f)
    def decorated(*args, **kwargs):
        # 1. 尝试从 Header 获取
        auth_header = request.headers.get('Authorization', '')
        
        token = None
        
        if auth_header.startswith('Bearer '):
            token = auth_header[7:]
        
        # 2. 如果没有，从查询参数获取
        if not token:
            token = request.args.get('token')
        
        # 3. 如果没有，从请求体获取
        if not token:
            data = request.get_json(silent=True) or {}
            token = data.get('token')
        
        if not token:
            return jsonify({
                'success': False,
                'error': 'Missing token',
                'message': '请在 Header (Authorization: Bearer <token>) 或请求参数中添加 token'
            }), 401
        
        # 验证 token
        result = verify_token(token, 'access')
        
        if not result['valid']:
            return jsonify({
                'success': False,
                'error': result.get('error', 'Invalid token')
            }), 401
        
        # 检查 token 是否已撤销
        jti = result['payload'].get('jti')
        if jti and is_token_revoked(jti):
            return jsonify({
                'success': False,
                'error': 'Token revoked',
                'message': 'Token 已被撤销，请重新获取'
            }), 401
        
        # 将 token 信息注入请求上下文
        request.jwt_payload = result['payload']
        request.api_key_id = result['api_key_id']
        
        return f(*args, **kwargs)
    
    return decorated


# ============================================================================
# API Key 验证中间件（保留兼容）
# ============================================================================

def require_api_key(f):
    """API Key 验证装饰器"""
    @wraps(f)
    def decorated(*args, **kwargs):
        # 1. 尝试从 URL 路径后缀获取（格式: /api/xxx/API_KEY）
        path = request.path.rstrip('/')
        parts = path.split('/')
        api_key = None
        
        # 检查最后一个部分是否是 API Key（以 bk_ 开头）
        if len(parts) > 1 and parts[-1].startswith('bk_'):
            api_key = parts[-1]
            # 重新设置请求路径，去掉 API Key
            request.path = '/'.join(parts[:-1])
        
        # 2. 如果没有，从查询参数获取
        if not api_key:
            api_key = request.args.get('api_key')
        
        # 3. 如果没有，从 Header 获取
        if not api_key:
            api_key = request.headers.get('X-API-Key')
        
        if not api_key:
            return jsonify({
                'success': False,
                'error': 'Missing API Key',
                'message': '请在 URL 后缀、查询参数或 Header 中添加 API Key'
            }), 401
        
        keys = load_keys()
        
        # 查找匹配的 key
        key_id = None
        
        for kid, kdata in keys.items():
            if kdata['key'] == api_key:
                key_id = kid
                break
        
        if not key_id:
            return jsonify({
                'success': False,
                'error': 'Invalid API Key',
                'message': 'API Key 无效'
            }), 401
        
        key_data = keys[key_id]
        
        if not key_data.get('is_active', True):
            return jsonify({
                'success': False,
                'error': 'API Key Disabled',
                'message': 'API Key 已被禁用'
            }), 403
        
        # 更新最后使用时间
        key_data['last_used'] = datetime.now().isoformat()
        save_keys(keys)
        
        # 将 key_id 注入到请求上下文
        request.api_key_id = key_id
        
        return f(*args, **kwargs)
    
    return decorated

# ============================================================================
# DashScope API 集成（添加认证保护）
# ============================================================================

from main import DashScopeClient, Config

@app.route('/api/chat', methods=['POST'])
@require_jwt_token
def chat():
    """对话接口（需要 JWT Token）"""
    try:
        data = request.get_json()
        
        if not data or 'messages' not in data:
            return jsonify({
                'success': False,
                'error': 'Missing required parameter: messages'
            }), 400
        
        # 获取任务名称（通常是对话内容的前几个字）
        messages = data['messages']
        task_name = "AI对话"
        if messages:
            last_message = messages[-1]
            if isinstance(last_message, dict):
                content = last_message.get('content', '')[:20]
                if content:
                    task_name = f"对话: {content}..."
        
        # 使用任务跟踪包装对话
        with ConversationTask(task_name) as task:
            task.update(10, "正在理解问题...")
            
            model = data.get('model', Config.DEFAULT_MODEL)
            temperature = data.get('temperature', 0.7)
            max_tokens = data.get('max_tokens', 2000)
            
            client = DashScopeClient(model=model)
            
            task.update(30, "正在生成回答...")
            response = client.chat(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            task.update(90, "回答生成完成...")
        
        return jsonify({
            'success': True,
            'data': response,
            'task_id': task.id,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/models', methods=['GET'])
def list_models():
    """获取支持的模型列表（无需认证）"""
    return jsonify({
        'models': Config.SUPPORTED_MODELS,
        'default': Config.DEFAULT_MODEL
    })

@app.route('/health', methods=['GET'])
def health_check():
    """健康检查（无需认证）"""
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.now().isoformat(),
        'service': 'dashscope-api'
    })

# ============================================================================
# CLI 命令
# ============================================================================

@app.cli.command('create-key')
def create_key_command():
    """创建 API Key（命令行）"""
    name = input('请输入 Key 名称: ').strip()
    if not name:
        print('名称不能为空')
        return
    
    keys = load_keys()
    new_key = generate_api_key()
    key_id = datetime.now().strftime('%Y%m%d%H%M%S')
    
    keys[key_id] = {
        'key': new_key,
        'name': name,
        'created_at': datetime.now().isoformat(),
        'last_used': None,
        'is_active': True
    }
    
    save_keys(keys)
    
    print(f'\n✅ API Key 创建成功!')
    print(f'ID: {key_id}')
    print(f'名称: {name}')
    print(f'Key: {new_key}')
    print('\n⚠️ 请保存好这个 Key，只显示一次!')

@app.cli.command('list-keys')
def list_keys_command():
    """列出所有 Keys（命令行）"""
    keys = load_keys()
    
    if not keys:
        print('暂无 API Keys')
        return
    
    print(f'\n📋 API Keys 列表 ({len(keys)} 个)')
    print('-' * 60)
    
    for key_id, kdata in keys.items():
        status = '✅' if kdata.get('is_active', True) else '❌'
        print(f'{status} [{key_id}] {kdata["name"]}')
        print(f'   创建: {kdata["created_at"][:10]}')
        print(f'   前缀: {kdata["key"][:15]}...')
        print()

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='API Key 认证服务')
    parser.add_argument('--port', type=int, default=5000, help='服务端口')
    parser.add_argument('--host', default='0.0.0.0', help='绑定地址')
    
    args = parser.parse_args()
    
    print(f'\n🚀 启动 API Key 认证服务...')
    print(f'   端口: {args.port}')
    print(f'   地址: http://{args.host}:{args.port}')
    print(f'\n管理接口:')
    print(f'   GET  /api/keys       - 列出 Keys')
    print(f'   POST /api/keys       - 创建 Key')
    print(f'   DELETE /api/keys/<id>- 删除 Key')
    print(f'\n认证后的 API:')
    print(f'   POST /api/chat       - 对话接口 (需要 X-API-Key)')
    print(f'\n示例:')
    print(f'   curl -H "X-API-Key: your_key" http://localhost:{args.port}/api/chat \\')
    print(f'        -H "Content-Type: application/json" \\')
    print(f'        -d \'{{"messages": [{{"role": "user", "content": "你好"}}]}}\'')
    print()
    
    app.run(host=args.host, port=args.port, debug=True)
