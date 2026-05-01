"""
WebSocket事件处理
实现实时进度推送
"""

import logging
from flask_socketio import SocketIO, emit, join_room, leave_room

logger = logging.getLogger(__name__)

# 创建SocketIO实例（将在app.py中初始化）
socketio = SocketIO(cors_allowed_origins="*", async_mode='threading')


def init_socketio(app):
    """初始化SocketIO"""
    socketio.init_app(app)
    return socketio


@socketio.on('connect')
def handle_connect():
    """客户端连接"""
    logger.info(f"客户端已连接: {getattr(socketio, 'server', 'unknown')}")
    emit('connected', {'data': 'Connected to server'})


@socketio.on('disconnect')
def handle_disconnect():
    """客户端断开连接"""
    logger.info("客户端已断开连接")


@socketio.on('join_task')
def handle_join_task(data):
    """客户端加入任务房间，接收该任务的进度更新"""
    task_id = data.get('task_id')
    if task_id:
        join_room(f"task_{task_id}")
        logger.info(f"客户端加入任务房间: {task_id}")
        emit('joined', {'task_id': task_id, 'status': 'joined'})


@socketio.on('leave_task')
def handle_leave_task(data):
    """客户端离开任务房间"""
    task_id = data.get('task_id')
    if task_id:
        leave_room(f"task_{task_id}")
        logger.info(f"客户端离开任务房间: {task_id}")
        emit('left', {'task_id': task_id, 'status': 'left'})


def emit_task_progress(task_id: str, progress: int, message: str = ""):
    """
    向任务房间广播进度更新
    
    Args:
        task_id: 任务ID
        progress: 进度百分比（0-100）
        message: 进度消息
    """
    try:
        room = f"task_{task_id}"
        socketio.emit('task_progress', {
            'task_id': task_id,
            'progress': progress,
            'message': message
        }, room=room)
        logger.debug(f"进度推送: {task_id} - {progress}% - {message}")
    except Exception as e:
        logger.error(f"推送进度失败: {e}")


def emit_task_complete(task_id: str, result: dict):
    """
    向任务房间广播任务完成
    
    Args:
        task_id: 任务ID
        result: 任务结果
    """
    try:
        room = f"task_{task_id}"
        socketio.emit('task_complete', {
            'task_id': task_id,
            'result': result
        }, room=room)
        logger.info(f"任务完成推送: {task_id}")
    except Exception as e:
        logger.error(f"推送任务完成失败: {e}")


def emit_task_failed(task_id: str, error: str):
    """
    向任务房间广播任务失败
    
    Args:
        task_id: 任务ID
        error: 错误信息
    """
    try:
        room = f"task_{task_id}"
        socketio.emit('task_failed', {
            'task_id': task_id,
            'error': error
        }, room=room)
        logger.error(f"任务失败推送: {task_id} - {error}")
    except Exception as e:
        logger.error(f"推送任务失败失败: {e}")


# 导出
__all__ = [
    'socketio',
    'init_socketio',
    'emit_task_progress',
    'emit_task_complete',
    'emit_task_failed'
]