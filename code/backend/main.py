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
import time
from datetime import datetime
from typing import Optional, Dict, Any, List

# 尝试导入 requests，如果不存在则提示安装
try:
    import requests
except ImportError:
    print("❌ 缺少依赖库，请运行: pip install requests")
    sys.exit(1)


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
    from flask import Flask, request, jsonify
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False
    print("⚠️ Flask 未安装，运行测试需要安装: pip install flask")

if FLASK_AVAILABLE:
    app = Flask(__name__)
    
    # 全局客户端实例
    _client: Optional[DashScopeClient] = None
    
    def get_client() -> DashScopeClient:
        """获取或创建客户端实例"""
        global _client
        if _client is None:
            _client = DashScopeClient()
        return _client
    
    @app.route('/health', methods=['GET'])
    def health_check():
        """健康检查接口"""
        return jsonify({
            'status': 'ok',
            'timestamp': datetime.now().isoformat(),
            'service': 'dashscope-api'
        })
    
    @app.route('/api/chat', methods=['POST'])
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
        try:
            data = request.get_json()
            
            # 参数验证
            if not data or 'messages' not in data:
                return jsonify({
                    'error': 'Missing required parameter: messages'
                }), 400
            
            messages = data['messages']
            model = data.get('model', Config.DEFAULT_MODEL)
            temperature = data.get('temperature', 0.7)
            max_tokens = data.get('max_tokens', 2000)
            
            # 创建客户端并调用 API
            client = DashScopeClient(model=model)
            response = client.chat(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            return jsonify({
                'success': True,
                'data': response,
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/api/models', methods=['GET'])
    def list_models():
        """获取支持的模型列表"""
        return jsonify({
            'models': Config.SUPPORTED_MODELS,
            'default': Config.DEFAULT_MODEL
        })
    
    @app.route('/api/config', methods=['GET'])
    def get_config():
        """获取当前配置（不包含敏感信息）"""
        return jsonify({
            'api_key_configured': bool(Config.DASHSCOPE_API_KEY),
            'base_url': Config.DASHSCOPE_BASE_URL,
            'default_model': Config.DEFAULT_MODEL,
            'supported_models': Config.SUPPORTED_MODELS
        })


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
        print(f"\n🚀 启动 Web 服务...")
        print(f"   端口: {args.port}")
        print(f"   健康检查: http://localhost:{args.port}/health")
        print(f"   对话接口: POST http://localhost:{args.port}/api/chat")
        app.run(host='0.0.0.0', port=args.port, debug=True)
    else:
        # 默认运行测试
        run_all_tests()


if __name__ == '__main__':
    main()
