#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
任务队列管理系统
用于跟踪 AI 对话任务的执行状态
"""

import uuid
import json
import threading
import time
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional
from dataclasses import dataclass, field, asdict
from collections import defaultdict
from flask import jsonify, request


class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"       # 等待中
    PROCESSING = "processing" # 处理中
    COMPLETED = "completed"   # 已完成
    FAILED = "failed"         # 失败


@dataclass
class Task:
    """任务数据类"""
    id: str
    name: str
    status: str
    progress: int  # 0-100
    message: str
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    metadata: Dict = field(default_factory=dict)
    
    def to_dict(self):
        return asdict(self)


class TaskManager:
    """任务管理器（单例模式）"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._tasks: Dict[str, Task] = {}
                    cls._instance._max_tasks = 100  # 最多保留100个任务
        return cls._instance
    
    def create_task(self, name: str, metadata: Dict = None) -> Task:
        """创建新任务"""
        task_id = str(uuid.uuid4())[:8]
        
        task = Task(
            id=task_id,
            name=name,
            status=TaskStatus.PENDING.value,
            progress=0,
            message="任务已创建，等待处理",
            created_at=datetime.now().isoformat(),
            metadata=metadata or {}
        )
        
        self._tasks[task_id] = task
        self._cleanup_old_tasks()
        
        return task
    
    def start_task(self, task_id: str, message: str = "开始处理") -> Optional[Task]:
        """开始执行任务"""
        task = self._tasks.get(task_id)
        if task:
            task.status = TaskStatus.PROCESSING.value
            task.started_at = datetime.now().isoformat()
            task.message = message
        return task
    
    def update_progress(self, task_id: str, progress: int, message: str = None):
        """更新任务进度"""
        task = self._tasks.get(task_id)
        if task:
            task.progress = max(0, min(100, progress))
            if message:
                task.message = message
    
    def complete_task(self, task_id: str, message: str = "任务完成"):
        """完成任务"""
        task = self._tasks.get(task_id)
        if task:
            task.status = TaskStatus.COMPLETED.value
            task.progress = 100
            task.completed_at = datetime.now().isoformat()
            task.message = message
    
    def fail_task(self, task_id: str, message: str = "任务失败"):
        """任务失败"""
        task = self._tasks.get(task_id)
        if task:
            task.status = TaskStatus.FAILED.value
            task.completed_at = datetime.now().isoformat()
            task.message = message
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """获取任务详情"""
        return self._tasks.get(task_id)
    
    def get_all_tasks(self) -> List[Task]:
        """获取所有任务（按创建时间倒序）"""
        tasks = list(self._tasks.values())
        tasks.sort(key=lambda x: x.created_at, reverse=True)
        return tasks
    
    def get_active_tasks(self) -> List[Task]:
        """获取正在处理的任务"""
        return [
            t for t in self._tasks.values()
            if t.status == TaskStatus.PROCESSING.value
        ]
    
    def get_recent_tasks(self, limit: int = 10) -> List[Task]:
        """获取最近的任务"""
        tasks = self.get_all_tasks()[:limit]
        return tasks
    
    def get_statistics(self) -> Dict:
        """获取任务统计"""
        tasks = list(self._tasks.values())
        
        stats = {
            "total": len(tasks),
            "pending": 0,
            "processing": 0,
            "completed": 0,
            "failed": 0
        }
        
        for task in tasks:
            if task.status in stats:
                stats[task.status] += 1
        
        return stats
    
    def _cleanup_old_tasks(self):
        """清理旧任务（保留最近的任务）"""
        while len(self._tasks) > self._max_tasks:
            # 删除最早的任务
            oldest_id = min(
                self._tasks.keys(),
                key=lambda x: self._tasks[x].created_at
            )
            del self._tasks[oldest_id]
    
    def clear_completed(self):
        """清除已完成的任务"""
        self._tasks = {
            k: v for k, v in self._tasks.items()
            if v.status != TaskStatus.COMPLETED.value
        }
    
    def clear_all(self):
        """清除所有任务"""
        self._tasks.clear()


# 全局任务管理器实例
task_manager = TaskManager()


# ============================================================================
# Flask API 集成
# ============================================================================

def register_task_routes(app):
    """注册任务管理 API 路由"""
    
    @app.route('/api/tasks', methods=['GET'])
    def list_tasks():
        """获取任务列表"""
        limit = request.args.get('limit', 10, type=int)
        status = request.args.get('status')
        
        if status:
            tasks = [
                t for t in task_manager.get_all_tasks()
                if t.status == status
            ][:limit]
        else:
            tasks = task_manager.get_recent_tasks(limit)
        
        return jsonify({
            'success': True,
            'tasks': [t.to_dict() for t in tasks],
            'total': len(tasks)
        })
    
    @app.route('/api/tasks/<task_id>', methods=['GET'])
    def get_task(task_id):
        """获取任务详情"""
        task = task_manager.get_task(task_id)
        if task:
            return jsonify({
                'success': True,
                'task': task.to_dict()
            })
        return jsonify({
            'success': False,
            'error': '任务不存在'
        }), 404
    
    @app.route('/api/tasks/statistics', methods=['GET'])
    def get_task_statistics():
        """获取任务统计"""
        stats = task_manager.get_statistics()
        return jsonify({
            'success': True,
            'statistics': stats
        })
    
    @app.route('/api/tasks/active', methods=['GET'])
    def get_active_tasks():
        """获取正在处理的任务"""
        tasks = task_manager.get_active_tasks()
        return jsonify({
            'success': True,
            'tasks': [t.to_dict() for t in tasks],
            'count': len(tasks)
        })
    
    @app.route('/api/tasks', methods=['DELETE'])
    def clear_tasks():
        """清除任务"""
        action = request.args.get('action', 'completed')
        
        if action == 'all':
            task_manager.clear_all()
        else:
            task_manager.clear_completed()
        
        return jsonify({
            'success': True,
            'message': f'已清除{action}任务'
        })


# ============================================================================
# 示例：AI 对话任务跟踪
# ============================================================================

class ConversationTask:
    """对话任务包装器"""
    
    def __init__(self, name: str = "AI对话"):
        self.task_id = None
        self.name = name
    
    def __enter__(self):
        """开始任务"""
        self.task_id = task_manager.create_task(self.name).id
        task_manager.start_task(self.task_id, "正在思考...")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """结束任务"""
        if exc_type is None:
            task_manager.complete_task(self.task_id, "对话完成")
        else:
            task_manager.fail_task(self.task_id, f"错误: {str(exc_val)}")
        return False  # 不抑制异常
    
    def update(self, progress: int, message: str = None):
        """更新进度"""
        task_manager.update_progress(self.task_id, progress, message)
    
    @property
    def id(self):
        return self.task_id


# 使用示例
if __name__ == '__main__':
    # 示例用法
    with ConversationTask("测试对话") as task:
        task.update(20, "正在理解问题...")
        task.update(60, "正在生成回答...")
        task.update(90, "正在润色回答...")
        # 任务完成自动标记
