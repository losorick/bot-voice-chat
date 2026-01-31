#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
对话历史管理器

功能：
- 保存对话记录到文件
- 查询历史对话
- 管理对话会话

作者: Bot Voice Team
创建时间: 2026-01-31
"""

import os
import json
import uuid
import shutil
from datetime import datetime
from typing import Optional, Dict, Any, List
from threading import Lock


class HistoryManager:
    """对话历史管理器"""
    
    def __init__(self, storage_dir: str = None):
        """
        初始化历史管理器
        
        Args:
            storage_dir: 历史记录存储目录 (默认: ./data/history)
        """
        if storage_dir is None:
            # 默认存储到项目目录下的 data/history
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            storage_dir = os.path.join(base_dir, 'data', 'history')
        
        self.storage_dir = storage_dir
        self.history_file = os.path.join(storage_dir, 'conversations.json')
        self.lock = Lock()
        
        # 确保存储目录存在
        os.makedirs(storage_dir, exist_ok=True)
        
        # 初始化历史文件
        if not os.path.exists(self.history_file):
            self._save_to_file([])
    
    def _load_from_file(self) -> List[Dict[str, Any]]:
        """从文件加载历史记录"""
        try:
            with open(self.history_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return []
    
    def _save_to_file(self, data: List[Dict[str, Any]]) -> None:
        """保存历史记录到文件"""
        with open(self.history_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def create_conversation(self, title: str = None, system_prompt: str = None) -> Dict[str, Any]:
        """
        创建新对话会话
        
        Args:
            title: 对话标题 (默认自动生成)
            system_prompt: 系统提示词
            
        Returns:
            创建的对话会话信息
        """
        with self.lock:
            conversation_id = str(uuid.uuid4())[:8]
            timestamp = datetime.now().isoformat()
            
            conversation = {
                'id': conversation_id,
                'title': title or f'新对话 {timestamp}',
                'system_prompt': system_prompt,
                'messages': [],
                'created_at': timestamp,
                'updated_at': timestamp,
                'token_usage': {'input': 0, 'output': 0}
            }
            
            # 加载现有历史
            history = self._load_from_file()
            
            # 添加新对话
            history.insert(0, conversation)
            
            # 保存
            self._save_to_file(history)
            
            return conversation
    
    def add_message(self, conversation_id: str, role: str, content: str, 
                   token_count: int = None) -> Optional[Dict[str, Any]]:
        """
        添加消息到对话
        
        Args:
            conversation_id: 对话 ID
            role: 角色 (user/assistant/system)
            content: 消息内容
            token_count: Token 数量
            
        Returns:
            添加的消息对象，失败返回 None
        """
        with self.lock:
            history = self._load_from_file()
            
            for conv in history:
                if conv['id'] == conversation_id:
                    message = {
                        'id': str(uuid.uuid4())[:8],
                        'role': role,
                        'content': content,
                        'timestamp': datetime.now().isoformat(),
                        'token_count': token_count
                    }
                    
                    conv['messages'].append(message)
                    conv['updated_at'] = datetime.now().isoformat()
                    
                    # 更新 token 使用统计
                    if token_count:
                        if role == 'user':
                            conv['token_usage']['input'] += token_count
                        else:
                            conv['token_usage']['output'] += token_count
                    
                    self._save_to_file(history)
                    return message
            
            return None
    
    def get_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """
        获取对话详情
        
        Args:
            conversation_id: 对话 ID
            
        Returns:
            对话信息，未找到返回 None
        """
        history = self._load_from_file()
        for conv in history:
            if conv['id'] == conversation_id:
                return conv
        return None
    
    def get_conversations(self, limit: int = 20, offset: int = 0) -> Dict[str, Any]:
        """
        获取对话列表
        
        Args:
            limit: 返回数量限制
            offset: 偏移量
            
        Returns:
            对话列表和分页信息
        """
        history = self._load_from_file()
        
        total = len(history)
        conversations = history[offset:offset + limit]
        
        # 移除消息内容，只返回基本信息
        preview = []
        for conv in conversations:
            preview.append({
                'id': conv['id'],
                'title': conv['title'],
                'created_at': conv['created_at'],
                'updated_at': conv['updated_at'],
                'message_count': len(conv['messages']),
                'token_usage': conv['token_usage']
            })
        
        return {
            'conversations': preview,
            'total': total,
            'limit': limit,
            'offset': offset
        }
    
    def delete_conversation(self, conversation_id: str) -> bool:
        """
        删除对话
        
        Args:
            conversation_id: 对话 ID
            
        Returns:
            是否删除成功
        """
        with self.lock:
            history = self._load_from_file()
            
            original_length = len(history)
            history = [conv for conv in history if conv['id'] != conversation_id]
            
            if len(history) < original_length:
                self._save_to_file(history)
                return True
            return False
    
    def clear_all(self) -> int:
        """
        清空所有对话历史
        
        Returns:
            删除的对话数量
        """
        with self.lock:
            history = self._load_from_file()
            count = len(history)
            
            if count > 0:
                # 备份旧数据
                backup_file = os.path.join(
                    self.storage_dir, 
                    f'conversations_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
                )
                shutil.copy(self.history_file, backup_file)
                
                # 清空
                self._save_to_file([])
            
            return count
    
    def export_conversation(self, conversation_id: str, format: str = 'json') -> Optional[str]:
        """
        导出对话内容
        
        Args:
            conversation_id: 对话 ID
            format: 导出格式 ('json' 或 'text')
            
        Returns:
            导出内容，失败返回 None
        """
        conversation = self.get_conversation(conversation_id)
        if not conversation:
            return None
        
        if format == 'text':
            lines = [f"# {conversation['title']}\n"]
            lines.append(f"创建时间: {conversation['created_at']}\n")
            lines.append(f"最后更新: {conversation['updated_at']}\n")
            lines.append("-" * 40 + "\n")
            
            for msg in conversation['messages']:
                role_name = {'user': '用户', 'assistant': '助手', 'system': '系统'}.get(
                    msg['role'], msg['role']
                )
                lines.append(f"**{role_name}** ({msg['timestamp']}):\n")
                lines.append(f"{msg['content']}\n\n")
            
            return ''.join(lines)
        else:
            return json.dumps(conversation, ensure_ascii=False, indent=2)
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取统计信息
        
        Returns:
            统计数据字典
        """
        history = self._load_from_file()
        
        total_conversations = len(history)
        total_messages = sum(len(conv['messages']) for conv in history)
        total_tokens = sum(
            conv['token_usage']['input'] + conv['token_usage']['output'] 
            for conv in history
        )
        
        # 按日期统计
        date_stats = {}
        for conv in history:
            date = conv['created_at'][:10]
            if date not in date_stats:
                date_stats[date] = {'conversations': 0, 'messages': 0}
            date_stats[date]['conversations'] += 1
            date_stats[date]['messages'] += len(conv['messages'])
        
        return {
            'total_conversations': total_conversations,
            'total_messages': total_messages,
            'total_tokens': total_tokens,
            'storage_dir': self.storage_dir,
            'storage_file': self.history_file,
            'date_stats': date_stats
        }


# 全局实例
_history_manager: Optional[HistoryManager] = None


def get_history_manager(storage_dir: str = None) -> HistoryManager:
    """获取历史管理器单例"""
    global _history_manager
    if _history_manager is None:
        _history_manager = HistoryManager(storage_dir)
    return _history_manager
