"""
Celery应用配置
支持SQLite和Redis作为Broker
"""

import os
from celery import Celery
from celery.signals import task_prerun, task_postrun, task_failure

# 创建Celery应用实例
celery_app = Celery('car_recognition')

# 配置Celery
def configure_celery():
    """配置Celery，支持SQLite和Redis"""
    
    # 从环境变量获取Broker类型
    broker_type = os.getenv('CELERY_BROKER_TYPE', 'sqlalchemy').lower()
    
    if broker_type == 'sqlalchemy':
        # SQLite作为Broker（开发/测试用，零配置）
        # 使用SQLAlchemy作为消息队列
        broker_url = 'sqla+sqlite:///celery_broker.db'
        result_backend = 'db+sqlite:///celery_results.db'
        
    elif broker_type == 'redis':
        # Redis作为Broker（生产环境）
        redis_host = os.getenv('REDIS_HOST', 'localhost')
        redis_port = os.getenv('REDIS_PORT', '6379')
        redis_db = os.getenv('REDIS_DB', '0')
        
        broker_url = f'redis://{redis_host}:{redis_port}/{redis_db}'
        result_backend = f'redis://{redis_host}:{redis_port}/{int(redis_db)+1}'
        
    else:
        raise ValueError(f"未知的Broker类型: {broker_type}，可选: sqlalchemy, redis")
    
    celery_app.conf.update(
        # Broker配置
        broker_url=broker_url,
        result_backend=result_backend,
        
        # 序列化配置
        task_serializer='json',
        accept_content=['json'],
        result_serializer='json',
        
        # 时区配置
        timezone='Asia/Shanghai',
        enable_utc=True,
        
        # 任务结果过期时间（1天）
        result_expires=86400,
        
        # 任务追踪
        task_track_started=True,
        task_time_limit=300,  # 5分钟超时
        task_soft_time_limit=240,  # 4分钟软超时
        
        # 并发配置 - 云端GPU单并发，本地设1防止OOM
        worker_concurrency=1,  # 单并发处理，避免显存溢出
        worker_prefetch_multiplier=1,  # 公平调度
        worker_max_tasks_per_child=50,  # 处理50个任务后重启worker，防止内存泄漏
        
        # 日志配置
        worker_hijack_root_logger=False,
    )
    
    return celery_app

# 初始化配置
configure_celery()

# 自动发现任务模块
# 使用绝对导入路径
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
celery_app.autodiscover_tasks(['tasks'])


# ========== 任务信号处理 ==========

@task_prerun.connect
def task_prerun_handler(task_id, task, args, kwargs, **extras):
    """任务开始前的处理"""
    from celery.utils.log import get_task_logger
    logger = get_task_logger(__name__)
    logger.info(f"任务开始: {task.name}[{task_id}]")


@task_postrun.connect
def task_postrun_handler(task_id, task, args, kwargs, retval, state, **extras):
    """任务完成后的处理"""
    from celery.utils.log import get_task_logger
    logger = get_task_logger(__name__)
    logger.info(f"任务完成: {task.name}[{task_id}] 状态: {state}")


@task_failure.connect
def task_failure_handler(task_id, exception, args, kwargs, traceback, einfo, **extras):
    """任务失败时的处理"""
    from celery.utils.log import get_task_logger
    logger = get_task_logger(__name__)
    logger.error(f"任务失败: {task_id} 错误: {exception}")


# 导出应用实例
__all__ = ['celery_app']