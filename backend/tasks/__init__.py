"""
Celery任务模块
包含车辆识别等异步任务
"""

from .recognition import recognize_vehicle_task, get_task_status

__all__ = ['recognize_vehicle_task', 'get_task_status']