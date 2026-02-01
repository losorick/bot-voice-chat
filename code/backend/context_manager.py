#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
对话上下文管理器

功能：
- 管理多轮对话上下文
- 上下文窗口管理（限制最大消息数）
- 内存存储支持

作者: Bot Voice Team
创建时间: 2026-02-02
"""

import os
import json
import uuid
import threading
from datetime import datetime
from typing import Optional, Dict, Any, List
from collections import OrderedDict


class ContextManager:
    """
    对话上下文管理器
    
    支持：
    - 内存存储对话上下文
    - 上下文窗口管理（限制最大消息数）
    - 自动清理过期上下文
    """
    
    # 默认配置
    DEFAULT_MAX_MESSAGES = 20  # 默认最大消息数
    DEFAULT_SESSION_TIMEOUT = 3600  # 会话超时时间（秒）
    
    def __init__(self, max_messages: int = None, session_timeout: int = None):
        """
        初始化上下文管理器
        
        Args:
            max_messages: 每个会话最大消息数（默认 20）
            session_timeout: 会话超时时间（秒，默认 1小时）
        """
        self.max_messages = max_messages or self.DEFAULT_MAX_MESSAGES
        self.session_timeout = session_timeout or self.DEFAULT_SESSION_TIMEOUT
        
        # 内存存储：{session_id: {...}}
        self._sessions: Dict[str, Dict[str, Any]] = {}
        
        # 线程锁
        self._lock = threading.RLock()
        
        # 定期清理任务
        self._cleanup_thread: Optional[threading.Thread] = None
        self._running = False
        
        # 启动后台清理任务
        self._start_cleanup_task()
    
    def _start_cleanup_task(self):
        """启动后台清理任务"""
        if self._cleanup_thread is not None and self._cleanup_thread.is_alive():
            return
            
        self._running = True
        self._cleanup_thread = threading.Thread(target=self._cleanup_expired_sessions, daemon=True)
        self._cleanup_thread.start()
    
    def _cleanup_expired_sessions(self):
        """定期清理过期会话"""
        while self._running:
            try:
                self.cleanup_expired()
            except Exception:
                pass
            # 每分钟检查一次
            threading.sleep(60)
    
    def stop(self):
        """停止清理任务"""
        self._running = False
        if self._cleanup_thread:
            self._cleanup_thread.join(timeout=5)
    
    def create_session(self, session_id: str = None, system_prompt: str = None) -> Dict[str, Any]:
        """
        创建新会话
        
        Args:
            session_id: 会话 ID（默认自动生成）
            system_prompt: 系统提示词
            
        Returns:
            会话信息字典
        """
        with self._lock:
            session_id = session_id or str(uuid.uuid4())[:8]
            timestamp = datetime.now().isoformat()
            
            session = {
                'id': session_id,
                'system_prompt': system_prompt,
                'messages': [],  # 消息列表 [{"role": "user", "content": "xxx"}, ...]
                'created_at': timestamp,
                'updated_at': timestamp,
                'message_count': 0,
                'token_usage': {'input': 0, 'output': 0}
            }
            
            self._sessions[session_id] = session
            return session
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        获取会话信息
        
        Args:
            session_id: 会话 ID
            
        Returns:
            会话信息，未找到返回 None
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if session:
                # 更新最后活跃时间
                session['updated_at'] = datetime.now().isoformat()
            return session
    
    def add_message(self, session_id: str, role: str, content: str,
                   token_count: int = None) -> Optional[Dict[str, Any]]:
        """
        添加消息到会话
        
        Args:
            session_id: 会话 ID
            role: 角色 (user/assistant/system)
            content: 消息内容
            token_count: Token 数量
            
        Returns:
            添加的消息对象，失败返回 None
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                return None
            
            message = {
                'id': str(uuid.uuid4())[:8],
                'role': role,
                'content': content,
                'timestamp': datetime.now().isoformat(),
                'token_count': token_count
            }
            
            session['messages'].append(message)
            session['message_count'] = len(session['messages'])
            session['updated_at'] = datetime.now().isoformat()
            
            # 更新 token 使用统计
            if token_count:
                if role == 'user':
                    session['token_usage']['input'] += token_count
                else:
                    session['token_usage']['output'] += token_count
            
            # 上下文窗口管理：检查是否超出最大消息数
            if len(session['messages']) > self.max_messages:
                # 保留 system prompt（如有）和最近的 max_messages 条消息
                kept_messages = session['messages'][-(self.max_messages):]
                session['messages'] = kept_messages
                session['message_count'] = len(kept_messages)
            
            return message
    
    def get_messages(self, session_id: str, include_system_prompt: bool = True) -> List[Dict[str, str]]:
        """
        获取会话消息列表（用于 API 调用）
        
        Args:
            session_id: 会话 ID
            include_system_prompt: 是否包含系统提示词
            
        Returns:
            消息列表 [{"role": "xxx", "content": "xxx"}, ...]
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                return []
            
            messages = []
            
            # 添加系统提示词（如有）
            if include_system_prompt and session.get('system_prompt'):
                messages.append({
                    'role': 'system',
                    'content': session['system_prompt']
                })
            
            # 添加对话消息
            for msg in session['messages']:
                messages.append({
                    'role': msg['role'],
                    'content': msg['content']
                })
            
            return messages
    
    def get_conversation_history(self, session_id: str) -> List[Dict[str, Any]]:
        """
        获取会话完整历史
        
        Args:
            session_id: 会话 ID
            
        Returns:
            完整消息历史列表
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                return []
            return session['messages'].copy()
    
    def update_system_prompt(self, session_id: str, system_prompt: str) -> bool:
        """
        更新系统提示词
        
        Args:
            session_id: 会话 ID
            system_prompt: 新的系统提示词
            
        Returns:
            是否更新成功
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                return False
            
            session['system_prompt'] = system_prompt
            session['updated_at'] = datetime.now().isoformat()
            return True
    
    def delete_session(self, session_id: str) -> bool:
        """
        删除会话
        
        Args:
            session_id: 会话 ID
            
        Returns:
            是否删除成功
        """
        with self._lock:
            if session_id in self._sessions:
                del self._sessions[session_id]
                return True
            return False
    
    def cleanup_expired(self) -> int:
        """
        清理过期会话
        
        Returns:
            清理的会话数量
        """
        now = datetime.now().timestamp()
        expired_sessions = []
        
        with self._lock:
            for session_id, session in self._sessions.items():
                updated_at = datetime.fromisoformat(session['updated_at']).timestamp()
                if now - updated_at > self.session_timeout:
                    expired_sessions.append(session_id)
            
            for session_id in expired_sessions:
                del self._sessions[session_id]
        
        return len(expired_sessions)
    
    def clear_all(self) -> int:
        """
        清空所有会话
        
        Returns:
            清空的会话数量
        """
        with self._lock:
            count = len(self._sessions)
            self._sessions.clear()
            return count
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取统计信息
        
        Returns:
            统计数据字典
        """
        with self._lock:
            total_sessions = len(self._sessions)
            total_messages = sum(s['message_count'] for s in self._sessions.values())
            total_tokens = sum(
                s['token_usage']['input'] + s['token_usage']['output']
                for s in self._sessions.values()
            )
            
            # 按活跃时间分组
            active_sessions = sum(
                1 for s in self._sessions.values()
                if (datetime.now().timestamp() - 
                    datetime.fromisoformat(s['updated_at']).timestamp()) < 300
            )  # 5分钟内活跃
            
            return {
                'total_sessions': total_sessions,
                'total_messages': total_messages,
                'total_tokens': total_tokens,
                'active_sessions': active_sessions,
                'max_messages_per_session': self.max_messages,
                'session_timeout_seconds': self.session_timeout
            }
    
    def get_all_sessions(self) -> List[Dict[str, Any]]:
        """
        获取所有会话列表（基本信息）
        
        Returns:
            会话基本信息列表
        """
        with self._lock:
            return [
                {
                    'id': session['id'],
                    'message_count': session['message_count'],
                    'created_at': session['created_at'],
                    'updated_at': session['updated_at'],
                    'token_usage': session['token_usage']
                }
                for session in self._sessions.values()
            ]


# 全局实例
_context_manager: Optional[ContextManager] = None
_context_manager_lock = threading.Lock()


def get_context_manager(max_messages: int = None) -> ContextManager:
    """获取上下文管理器单例"""
    global _context_manager
    if _context_manager is None:
        with _context_manager_lock:
            if _context_manager is None:
                _context_manager = ContextManager(max_messages=max_messages)
    return _context_manager


def reset_context_manager():
    """重置上下文管理器（用于测试）"""
    global _context_manager
    if _context_manager:
        _context_manager.stop()
    _context_manager = None
