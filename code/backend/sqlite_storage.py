#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SQLite 对话历史持久化存储模块

功能：
- SQLite 数据库存储对话历史
- CRUD 操作接口
- 历史数据管理（查看、搜索、导出、删除）
- 自动备份和清理

作者: Bot Voice Team
创建时间: 2026-02-02
"""

import os
import sqlite3
import json
import threading
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path
import shutil


class SQLiteStorage:
    """
    SQLite 对话历史持久化存储
    
    支持：
    - 对话历史存储和读取
    - 搜索功能
    - 数据导出（JSON/CSV）
    - 自动备份
    """
    
    # 数据库文件名
    DB_FILENAME = 'conversations.db'
    
    # 备份配置
    BACKUP_DIR = 'backups'
    MAX_BACKUPS = 5  # 保留最近5个备份
    
    def __init__(self, db_path: str = None):
        """
        初始化存储管理器
        
        Args:
            db_path: 数据库文件路径（默认：当前目录下的 conversations.db）
        """
        if db_path is None:
            # 默认路径：当前工作目录下的 conversations.db
            self.db_path = os.path.join(os.getcwd(), self.DB_FILENAME)
        else:
            self.db_path = db_path
        
        # 确保目录存在
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        # 线程锁
        self._lock = threading.RLock()
        
        # 初始化数据库
        self._init_database()
    
    def _init_database(self):
        """初始化数据库表"""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 创建对话表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    system_prompt TEXT,
                    messages TEXT NOT NULL,  -- JSON 格式存储消息列表
                    message_count INTEGER DEFAULT 0,
                    token_usage TEXT,  -- JSON 格式存储 token 使用统计
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    metadata TEXT  -- JSON 格式存储其他元数据
                )
            ''')
            
            # 创建索引
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_session_id 
                ON conversations(session_id)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_updated_at 
                ON conversations(updated_at)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_created_at 
                ON conversations(created_at)
            ''')
            
            conn.commit()
            
            # 创建唤醒事件表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS wake_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    event_time TEXT NOT NULL,
                    trigger_type TEXT NOT NULL CHECK(trigger_type IN ('wake_word', 'manual')),
                    success BOOLEAN DEFAULT 1,
                    audio_duration FLOAT,
                    metadata TEXT
                )
            ''')
            
            # 创建唤醒事件索引
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_wake_events_session_id 
                ON wake_events(session_id)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_wake_events_event_time 
                ON wake_events(event_time)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_wake_events_trigger_type 
                ON wake_events(trigger_type)
            ''')
            
            conn.commit()
            conn.close()
    
    def _get_connection(self) -> sqlite3.Connection:
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        # 启用外键约束
        conn.execute('PRAGMA foreign_keys = ON')
        return conn
    
    # ========== CRUD 操作 ==========
    
    def create_conversation(self, conversation_id: str, session_id: str,
                           messages: List[Dict[str, Any]],
                           system_prompt: str = None,
                           token_usage: Dict[str, int] = None,
                           metadata: Dict[str, Any] = None) -> bool:
        """
        创建新对话记录
        
        Args:
            conversation_id: 对话 ID
            session_id: 会话 ID
            messages: 消息列表
            system_prompt: 系统提示词
            token_usage: Token 使用统计
            metadata: 其他元数据
            
        Returns:
            是否创建成功
        """
        with self._lock:
            try:
                conn = self._get_connection()
                cursor = conn.cursor()
                
                now = datetime.now().isoformat()
                messages_json = json.dumps(messages, ensure_ascii=False, indent=2)
                token_usage_json = json.dumps(token_usage or {'input': 0, 'output': 0}, ensure_ascii=False)
                metadata_json = json.dumps(metadata or {}, ensure_ascii=False)
                
                cursor.execute('''
                    INSERT INTO conversations 
                    (id, session_id, system_prompt, messages, message_count, 
                     token_usage, created_at, updated_at, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    conversation_id,
                    session_id,
                    system_prompt,
                    messages_json,
                    len(messages),
                    token_usage_json,
                    now,
                    now,
                    metadata_json
                ))
                
                conn.commit()
                conn.close()
                return True
            except Exception as e:
                print(f"[SQLiteStorage] 创建对话失败: {e}")
                return False
    
    def get_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """
        获取对话记录
        
        Args:
            conversation_id: 对话 ID
            
        Returns:
            对话记录字典，未找到返回 None
        """
        with self._lock:
            try:
                conn = self._get_connection()
                cursor = conn.cursor()
                
                cursor.execute('SELECT * FROM conversations WHERE id = ?', (conversation_id,))
                row = cursor.fetchone()
                conn.close()
                
                if row:
                    return self._row_to_conversation(row)
                return None
            except Exception as e:
                print(f"[SQLiteStorage] 获取对话失败: {e}")
                return None
    
    def update_conversation(self, conversation_id: str, 
                           messages: List[Dict[str, Any]] = None,
                           system_prompt: str = None,
                           token_usage: Dict[str, int] = None,
                           metadata: Dict[str, Any] = None) -> bool:
        """
        更新对话记录
        
        Args:
            conversation_id: 对话 ID
            messages: 消息列表
            system_prompt: 系统提示词
            token_usage: Token 使用统计
            metadata: 其他元数据
            
        Returns:
            是否更新成功
        """
        with self._lock:
            try:
                conn = self._get_connection()
                cursor = conn.cursor()
                
                # 构建更新语句
                updates = []
                params = []
                
                if messages is not None:
                    updates.append('messages = ?')
                    params.append(json.dumps(messages, ensure_ascii=False, indent=2))
                    updates.append('message_count = ?')
                    params.append(len(messages))
                
                if system_prompt is not None:
                    updates.append('system_prompt = ?')
                    params.append(system_prompt)
                
                if token_usage is not None:
                    updates.append('token_usage = ?')
                    params.append(json.dumps(token_usage, ensure_ascii=False))
                
                if metadata is not None:
                    updates.append('metadata = ?')
                    params.append(json.dumps(metadata, ensure_ascii=False))
                
                if updates:
                    updates.append('updated_at = ?')
                    params.append(datetime.now().isoformat())
                    params.append(conversation_id)
                    
                    sql = f'UPDATE conversations SET {", ".join(updates)} WHERE id = ?'
                    cursor.execute(sql, params)
                    conn.commit()
                
                conn.close()
                return True
            except Exception as e:
                print(f"[SQLiteStorage] 更新对话失败: {e}")
                return False
    
    def delete_conversation(self, conversation_id: str) -> bool:
        """
        删除对话记录
        
        Args:
            conversation_id: 对话 ID
            
        Returns:
            是否删除成功
        """
        with self._lock:
            try:
                conn = self._get_connection()
                cursor = conn.cursor()
                
                cursor.execute('DELETE FROM conversations WHERE id = ?', (conversation_id,))
                deleted_count = cursor.rowcount
                conn.commit()
                conn.close()
                
                return deleted_count > 0
            except Exception as e:
                print(f"[SQLiteStorage] 删除对话失败: {e}")
                return False
    
    # ========== 批量操作 ==========
    
    def get_conversations_by_session(self, session_id: str) -> List[Dict[str, Any]]:
        """
        获取会话的所有对话
        
        Args:
            session_id: 会话 ID
            
        Returns:
            对话记录列表
        """
        with self._lock:
            try:
                conn = self._get_connection()
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT * FROM conversations 
                    WHERE session_id = ? 
                    ORDER BY created_at DESC
                ''', (session_id,))
                
                rows = cursor.fetchall()
                conn.close()
                
                return [self._row_to_conversation(row) for row in rows]
            except Exception as e:
                print(f"[SQLiteStorage] 获取会话对话失败: {e}")
                return []
    
    def get_recent_conversations(self, limit: int = 50, 
                                  offset: int = 0) -> List[Dict[str, Any]]:
        """
        获取最近的对话
        
        Args:
            limit: 返回数量限制
            offset: 偏移量
            
        Returns:
            对话记录列表
        """
        with self._lock:
            try:
                conn = self._get_connection()
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT * FROM conversations 
                    ORDER BY updated_at DESC
                    LIMIT ? OFFSET ?
                ''', (limit, offset))
                
                rows = cursor.fetchall()
                conn.close()
                
                return [self._row_to_conversation(row) for row in rows]
            except Exception as e:
                print(f"[SQLiteStorage] 获取最近对话失败: {e}")
                return []
    
    # ========== 搜索功能 ==========
    
    def search_conversations(self, keyword: str, 
                             limit: int = 100) -> List[Dict[str, Any]]:
        """
        搜索对话内容
        
        Args:
            keyword: 搜索关键词
            limit: 返回数量限制
            
        Returns:
            匹配的对话记录列表
        """
        with self._lock:
            try:
                conn = self._get_connection()
                cursor = conn.cursor()
                
                # 在 messages 和 system_prompt 中搜索
                cursor.execute('''
                    SELECT * FROM conversations 
                    WHERE messages LIKE ? OR system_prompt LIKE ?
                    ORDER BY updated_at DESC
                    LIMIT ?
                ''', (f'%{keyword}%', f'%{keyword}%', limit))
                
                rows = cursor.fetchall()
                conn.close()
                
                return [self._row_to_conversation(row) for row in rows]
            except Exception as e:
                print(f"[SQLiteStorage] 搜索对话失败: {e}")
                return []
    
    def search_by_content(self, content: str, 
                         limit: int = 100) -> List[Tuple[Dict[str, Any], int]]:
        """
        搜索对话内容并返回匹配位置
        
        Args:
            content: 搜索内容
            limit: 返回数量限制
            
        Returns:
            (对话记录, 匹配消息索引) 列表
        """
        with self._lock:
            try:
                conn = self._get_connection()
                cursor = conn.cursor()
                
                cursor.execute('SELECT * FROM conversations ORDER BY updated_at DESC LIMIT ?', (limit,))
                rows = cursor.fetchall()
                conn.close()
                
                results = []
                for row in rows:
                    conv = self._row_to_conversation(row)
                    messages = conv.get('messages', [])
                    
                    for idx, msg in enumerate(messages):
                        msg_content = msg.get('content', '')
                        if content.lower() in msg_content.lower():
                            results.append((conv, idx))
                            break
                
                return results
            except Exception as e:
                print(f"[SQLiteStorage] 按内容搜索失败: {e}")
                return []
    
    # ========== 统计功能 ==========
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取统计数据
        
        Returns:
            统计信息字典
        """
        with self._lock:
            try:
                conn = self._get_connection()
                cursor = conn.cursor()
                
                # 总对话数
                cursor.execute('SELECT COUNT(*) FROM conversations')
                total_count = cursor.fetchone()[0]
                
                # 今日对话数
                today = datetime.now().strftime('%Y-%m-%d')
                cursor.execute('SELECT COUNT(*) FROM conversations WHERE date(created_at) = ?', (today,))
                today_count = cursor.fetchone()[0]
                
                # 总消息数
                cursor.execute('SELECT SUM(message_count) FROM conversations')
                total_messages = cursor.fetchone()[0] or 0
                
                # 按会话分组
                cursor.execute('SELECT session_id, COUNT(*) as cnt FROM conversations GROUP BY session_id')
                session_counts = cursor.fetchall()
                unique_sessions = len(session_counts)
                
                conn.close()
                
                return {
                    'total_conversations': total_count,
                    'today_conversations': today_count,
                    'total_messages': total_messages,
                    'unique_sessions': unique_sessions,
                    'database_size_bytes': os.path.getsize(self.db_path)
                }
            except Exception as e:
                print(f"[SQLiteStorage] 获取统计失败: {e}")
                return {}
    
    # ========== 导出功能 ==========
    
    def export_to_json(self, conversation_ids: List[str] = None,
                       format: str = 'json') -> str:
        """
        导出对话记录
        
        Args:
            conversation_ids: 要导出的对话 ID 列表（None 表示全部）
            format: 导出格式 ('json' 或 'jsonl')
            
        Returns:
            导出文件路径
        """
        with self._lock:
            try:
                conn = self._get_connection()
                cursor = conn.cursor()
                
                if conversation_ids:
                    placeholders = ','.join('?' * len(conversation_ids))
                    cursor.execute(f'SELECT * FROM conversations WHERE id IN ({placeholders})', 
                                   conversation_ids)
                else:
                    cursor.execute('SELECT * FROM conversations ORDER BY created_at DESC')
                
                rows = cursor.fetchall()
                conn.close()
                
                conversations = [self._row_to_conversation(row) for row in rows]
                
                # 生成文件名
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f'conversations_export_{timestamp}.{format}'
                file_path = os.path.join(os.getcwd(), filename)
                
                if format == 'json':
                    with open(file_path, 'w', encoding='utf-8') as f:
                        json.dump(conversations, f, ensure_ascii=False, indent=2)
                elif format == 'jsonl':
                    with open(file_path, 'w', encoding='utf-8') as f:
                        for conv in conversations:
                            f.write(json.dumps(conv, ensure_ascii=False) + '\n')
                
                return file_path
            except Exception as e:
                print(f"[SQLiteStorage] 导出失败: {e}")
                return ''
    
    def import_from_json(self, file_path: str) -> Tuple[int, int]:
        """
        从 JSON 文件导入对话记录
        
        Args:
            file_path: JSON 文件路径
            
        Returns:
            (成功数, 失败数)
        """
        with self._lock:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    conversations = json.load(f)
                
                if not isinstance(conversations, list):
                    conversations = [conversations]
                
                success_count = 0
                fail_count = 0
                
                conn = self._get_connection()
                cursor = conn.cursor()
                
                for conv in conversations:
                    try:
                        cursor.execute('''
                            INSERT OR REPLACE INTO conversations 
                            (id, session_id, system_prompt, messages, message_count, 
                             token_usage, created_at, updated_at, metadata)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            conv.get('id'),
                            conv.get('session_id'),
                            conv.get('system_prompt'),
                            json.dumps(conv.get('messages', []), ensure_ascii=False),
                            conv.get('message_count', 0),
                            json.dumps(conv.get('token_usage', {}), ensure_ascii=False),
                            conv.get('created_at'),
                            conv.get('updated_at'),
                            json.dumps(conv.get('metadata', {}), ensure_ascii=False)
                        ))
                        success_count += 1
                    except Exception:
                        fail_count += 1
                
                conn.commit()
                conn.close()
                
                return success_count, fail_count
            except Exception as e:
                print(f"[SQLiteStorage] 导入失败: {e}")
                return 0, 0
    
    # ========== 清理功能 ==========
    
    def cleanup_old_conversations(self, days: int = 30) -> int:
        """
        清理旧对话记录
        
        Args:
            days: 保留最近多少天的记录
            
        Returns:
            删除的记录数量
        """
        with self._lock:
            try:
                conn = self._get_connection()
                cursor = conn.cursor()
                
                # 计算日期阈值
                threshold = datetime.now().timestamp() - (days * 24 * 3600)
                threshold_date = datetime.fromtimestamp(threshold).strftime('%Y-%m-%d')
                
                cursor.execute('DELETE FROM conversations WHERE date(created_at) < ?', (threshold_date,))
                deleted_count = cursor.rowcount
                
                conn.commit()
                conn.close()
                
                # 尝试压缩数据库
                self.vacuum()
                
                return deleted_count
            except Exception as e:
                print(f"[SQLiteStorage] 清理旧对话失败: {e}")
                return 0
    
    def vacuum(self):
        """压缩数据库"""
        try:
            conn = self._get_connection()
            conn.execute('VACUUM')
            conn.close()
        except Exception as e:
            print(f"[SQLiteStorage] 数据库压缩失败: {e}")
    
    # ========== 备份功能 ==========
    
    def create_backup(self) -> str:
        """
        创建数据库备份
        
        Returns:
            备份文件路径
        """
        try:
            # 创建备份目录
            backup_dir = os.path.join(os.path.dirname(self.db_path), self.BACKUP_DIR)
            os.makedirs(backup_dir, exist_ok=True)
            
            # 生成备份文件名
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_path = os.path.join(backup_dir, f'conversations_backup_{timestamp}.db')
            
            # 复制数据库文件
            shutil.copy2(self.db_path, backup_path)
            
            # 清理旧备份
            self._cleanup_old_backups(backup_dir)
            
            return backup_path
        except Exception as e:
            print(f"[SQLiteStorage] 创建备份失败: {e}")
            return ''
    
    def _cleanup_old_backups(self, backup_dir: str):
        """清理旧备份文件"""
        try:
            backup_files = sorted(
                [f for f in os.listdir(backup_dir) if f.endswith('.db')],
                key=lambda x: os.path.getmtime(os.path.join(backup_dir, x)),
                reverse=True
            )
            
            for old_file in backup_files[self.MAX_BACKUPS:]:
                os.remove(os.path.join(backup_dir, old_file))
        except Exception:
            pass
    
    def restore_from_backup(self, backup_path: str) -> bool:
        """
        从备份恢复数据库
        
        Args:
            backup_path: 备份文件路径
            
        Returns:
            是否恢复成功
        """
        try:
            if not os.path.exists(backup_path):
                return False
            
            # 关闭当前连接（通过创建新连接确保锁释放）
            conn = self._get_connection()
            conn.close()
            
            # 备份当前数据库
            current_backup = self.create_backup()
            
            # 复制备份文件覆盖当前数据库
            shutil.copy2(backup_path, self.db_path)
            
            return True
        except Exception as e:
            print(f"[SQLiteStorage] 从备份恢复失败: {e}")
            return False
    
    # ========== 辅助方法 ==========
    
    def _row_to_conversation(self, row: sqlite3.Row) -> Dict[str, Any]:
        """将数据库行转换为对话字典"""
        try:
            messages = json.loads(row['messages']) if row['messages'] else []
        except json.JSONDecodeError:
            messages = []
        
        try:
            token_usage = json.loads(row['token_usage']) if row['token_usage'] else {}
        except json.JSONDecodeError:
            token_usage = {'input': 0, 'output': 0}
        
        try:
            metadata = json.loads(row['metadata']) if row['metadata'] else {}
        except json.JSONDecodeError:
            metadata = {}
        
        return {
            'id': row['id'],
            'session_id': row['session_id'],
            'system_prompt': row['system_prompt'],
            'messages': messages,
            'message_count': row['message_count'],
            'token_usage': token_usage,
            'created_at': row['created_at'],
            'updated_at': row['updated_at'],
            'metadata': metadata
        }
    
    def get_all_session_ids(self) -> List[str]:
        """获取所有会话 ID"""
        with self._lock:
            try:
                conn = self._get_connection()
                cursor = conn.cursor()
                
                cursor.execute('SELECT DISTINCT session_id FROM conversations ORDER BY created_at DESC')
                session_ids = [row[0] for row in cursor.fetchall()]
                
                conn.close()
                return session_ids
            except Exception as e:
                print(f"[SQLiteStorage] 获取会话 ID 列表失败: {e}")
                return []
    
    def close(self):
        """关闭数据库连接"""
        # SQLite 不需要显式关闭连接，但可以清理锁
        pass


# 全局实例
_storage: Optional[SQLiteStorage] = None
_storage_lock = threading.Lock()


def get_storage(db_path: str = None) -> SQLiteStorage:
    """获取存储管理器单例"""
    global _storage
    if _storage is None:
        with _storage_lock:
            if _storage is None:
                _storage = SQLiteStorage(db_path=db_path)
    return _storage


def reset_storage():
    """重置存储管理器（用于测试）"""
    global _storage
    if _storage:
        _storage.close()
    _storage = None


# ============================================================================
# 唤醒事件存储
# ============================================================================

class WakeEventStorage:
    """
    唤醒事件持久化存储
    
    支持：
    - 唤醒事件记录和查询
    - 统计分析和报告
    - 事件清理
    """
    
    def __init__(self, db_path: str = None):
        """
        初始化存储管理器
        
        Args:
            db_path: 数据库文件路径（默认使用主数据库）
        """
        if db_path is None:
            # 使用主数据库
            self.db_path = os.path.join(os.getcwd(), SQLiteStorage.DB_FILENAME)
        else:
            self.db_path = db_path
        
        self._lock = threading.RLock()
    
    def _get_connection(self) -> sqlite3.Connection:
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA foreign_keys = ON')
        return conn
    
    # ========== 唤醒事件 CRUD ==========
    
    def record_wake_event(self, session_id: str, trigger_type: str,
                          success: bool = True, audio_duration: float = None,
                          metadata: Dict[str, Any] = None) -> Optional[int]:
        """
        记录唤醒事件
        
        Args:
            session_id: 会话 ID
            trigger_type: 触发类型 ('wake_word' or 'manual')
            success: 是否成功
            audio_duration: 音频时长（秒）
            metadata: 其他元数据
            
        Returns:
            事件 ID，失败返回 None
        """
        with self._lock:
            try:
                conn = self._get_connection()
                cursor = conn.cursor()
                
                now = datetime.now().isoformat()
                metadata_json = json.dumps(metadata or {}, ensure_ascii=False)
                
                cursor.execute('''
                    INSERT INTO wake_events 
                    (session_id, event_time, trigger_type, success, audio_duration, metadata)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    session_id,
                    now,
                    trigger_type,
                    1 if success else 0,
                    audio_duration,
                    metadata_json
                ))
                
                event_id = cursor.lastrowid
                conn.commit()
                conn.close()
                
                return event_id
            except Exception as e:
                print(f"[WakeEventStorage] 记录唤醒事件失败: {e}")
                return None
    
    def get_wake_event(self, event_id: int) -> Optional[Dict[str, Any]]:
        """
        获取唤醒事件详情
        
        Args:
            event_id: 事件 ID
            
        Returns:
            事件字典，未找到返回 None
        """
        with self._lock:
            try:
                conn = self._get_connection()
                cursor = conn.cursor()
                
                cursor.execute('SELECT * FROM wake_events WHERE id = ?', (event_id,))
                row = cursor.fetchone()
                conn.close()
                
                if row:
                    return self._row_to_wake_event(row)
                return None
            except Exception as e:
                print(f"[WakeEventStorage] 获取唤醒事件失败: {e}")
                return None
    
    def get_wake_events_by_session(self, session_id: str, 
                                   limit: int = 100) -> List[Dict[str, Any]]:
        """
        获取会话的唤醒事件列表
        
        Args:
            session_id: 会话 ID
            limit: 返回数量限制
            
        Returns:
            事件列表
        """
        with self._lock:
            try:
                conn = self._get_connection()
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT * FROM wake_events 
                    WHERE session_id = ?
                    ORDER BY event_time DESC
                    LIMIT ?
                ''', (session_id, limit))
                
                rows = cursor.fetchall()
                conn.close()
                
                return [self._row_to_wake_event(row) for row in rows]
            except Exception as e:
                print(f"[WakeEventStorage] 获取会话唤醒事件失败: {e}")
                return []
    
    def get_recent_wake_events(self, limit: int = 100,
                               offset: int = 0) -> List[Dict[str, Any]]:
        """
        获取最近的唤醒事件
        
        Args:
            limit: 返回数量限制
            offset: 偏移量
            
        Returns:
            事件列表
        """
        with self._lock:
            try:
                conn = self._get_connection()
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT * FROM wake_events 
                    ORDER BY event_time DESC
                    LIMIT ? OFFSET ?
                ''', (limit, offset))
                
                rows = cursor.fetchall()
                conn.close()
                
                return [self._row_to_wake_event(row) for row in rows]
            except Exception as e:
                print(f"[WakeEventStorage] 获取最近唤醒事件失败: {e}")
                return []
    
    # ========== 唤醒事件统计 ==========
    
    def get_wake_stats(self, days: int = 7) -> Dict[str, Any]:
        """
        获取唤醒统计信息
        
        Args:
            days: 统计最近多少天的数据
            
        Returns:
            统计信息字典
        """
        with self._lock:
            try:
                conn = self._get_connection()
                cursor = conn.cursor()
                
                # 计算日期阈值
                threshold = datetime.now().timestamp() - (days * 24 * 3600)
                threshold_date = datetime.fromtimestamp(threshold).strftime('%Y-%m-%d %H:%M:%S')
                
                # 总唤醒次数
                cursor.execute('SELECT COUNT(*) FROM wake_events WHERE event_time >= ?', (threshold_date,))
                total_count = cursor.fetchone()[0]
                
                # 成功次数
                cursor.execute('SELECT COUNT(*) FROM wake_events WHERE event_time >= ? AND success = 1', (threshold_date,))
                success_count = cursor.fetchone()[0]
                
                # 按触发类型统计
                cursor.execute('''
                    SELECT trigger_type, COUNT(*) as cnt
                    FROM wake_events 
                    WHERE event_time >= ?
                    GROUP BY trigger_type
                ''', (threshold_date,))
                type_stats = {row['trigger_type']: row['cnt'] for row in cursor.fetchall()}
                
                # 今日唤醒次数
                today = datetime.now().strftime('%Y-%m-%d')
                cursor.execute('SELECT COUNT(*) FROM wake_events WHERE date(event_time) = ?', (today,))
                today_count = cursor.fetchone()[0]
                
                # 今日成功次数
                cursor.execute('SELECT COUNT(*) FROM wake_events WHERE date(event_time) = ? AND success = 1', (today,))
                today_success = cursor.fetchone()[0]
                
                # 平均音频时长
                cursor.execute('''
                    SELECT AVG(audio_duration) FROM wake_events 
                    WHERE event_time >= ? AND audio_duration IS NOT NULL
                ''', (threshold_date,))
                avg_duration = cursor.fetchone()[0] or 0
                
                # 按天统计（最近7天）
                cursor.execute('''
                    SELECT date(event_time) as date, COUNT(*) as count, AVG(success) as success_rate
                    FROM wake_events 
                    WHERE event_time >= ?
                    GROUP BY date(event_time)
                    ORDER BY date DESC
                    LIMIT ?
                ''', (threshold_date, days))
                daily_stats = [
                    {
                        'date': row['date'],
                        'count': row['count'],
                        'success_rate': round(row['success_rate'] * 100, 2)
                    }
                    for row in cursor.fetchall()
                ]
                
                conn.close()
                
                return {
                    'period_days': days,
                    'total_events': total_count,
                    'successful_events': success_count,
                    'success_rate': round(success_count / total_count * 100, 2) if total_count > 0 else 0,
                    'today_events': today_count,
                    'today_success': today_success,
                    'today_success_rate': round(today_success / today_count * 100, 2) if today_count > 0 else 0,
                    'by_trigger_type': type_stats,
                    'avg_audio_duration': round(avg_duration, 2),
                    'daily_stats': daily_stats,
                    'database_size_bytes': os.path.getsize(self.db_path)
                }
            except Exception as e:
                print(f"[WakeEventStorage] 获取统计失败: {e}")
                return {}
    
    # ========== 唤醒事件清理 ==========
    
    def cleanup_old_wake_events(self, days: int = 30) -> int:
        """
        清理旧唤醒事件
        
        Args:
            days: 保留最近多少天的记录
            
        Returns:
            删除的记录数量
        """
        with self._lock:
            try:
                conn = self._get_connection()
                cursor = conn.cursor()
                
                # 计算日期阈值
                threshold = datetime.now().timestamp() - (days * 24 * 3600)
                threshold_date = datetime.fromtimestamp(threshold).strftime('%Y-%m-%d %H:%M:%S')
                
                cursor.execute('DELETE FROM wake_events WHERE event_time < ?', (threshold_date,))
                deleted_count = cursor.rowcount
                
                conn.commit()
                conn.close()
                
                return deleted_count
            except Exception as e:
                print(f"[WakeEventStorage] 清理旧唤醒事件失败: {e}")
                return 0
    
    def clear_all_wake_events(self) -> int:
        """
        清空所有唤醒事件
        
        Returns:
            删除的记录数量
        """
        with self._lock:
            try:
                conn = self._get_connection()
                cursor = conn.cursor()
                
                cursor.execute('DELETE FROM wake_events')
                deleted_count = cursor.rowcount
                
                conn.commit()
                conn.close()
                
                return deleted_count
            except Exception as e:
                print(f"[WakeEventStorage] 清空唤醒事件失败: {e}")
                return 0
    
    # ========== 辅助方法 ==========
    
    def _row_to_wake_event(self, row: sqlite3.Row) -> Dict[str, Any]:
        """将数据库行转换为唤醒事件字典"""
        try:
            metadata = json.loads(row['metadata']) if row['metadata'] else {}
        except json.JSONDecodeError:
            metadata = {}
        
        return {
            'id': row['id'],
            'session_id': row['session_id'],
            'event_time': row['event_time'],
            'trigger_type': row['trigger_type'],
            'success': bool(row['success']),
            'audio_duration': row['audio_duration'],
            'metadata': metadata
        }
    
    def get_unique_session_ids(self) -> List[str]:
        """获取所有唯一会话 ID"""
        with self._lock:
            try:
                conn = self._get_connection()
                cursor = conn.cursor()
                
                cursor.execute('SELECT DISTINCT session_id FROM wake_events ORDER BY event_time DESC')
                session_ids = [row[0] for row in cursor.fetchall()]
                
                conn.close()
                return session_ids
            except Exception as e:
                print(f"[WakeEventStorage] 获取会话 ID 列表失败: {e}")
                return []
    
    def close(self):
        """关闭数据库连接"""
        pass


# 全局唤醒事件存储实例
_wake_storage: Optional[WakeEventStorage] = None
_wake_storage_lock = threading.Lock()


def get_wake_storage(db_path: str = None) -> WakeEventStorage:
    """获取唤醒事件存储单例"""
    global _wake_storage
    if _wake_storage is None:
        with _wake_storage_lock:
            if _wake_storage is None:
                _wake_storage = WakeEventStorage(db_path=db_path)
    return _wake_storage


def reset_wake_storage():
    """重置唤醒事件存储（用于测试）"""
    global _wake_storage
    _wake_storage = None
