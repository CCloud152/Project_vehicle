"""
车辆识别异步任务
"""

import os
import json
import logging
import uuid
from datetime import datetime
from typing import Optional, Dict, Any

from celery_app import celery_app
from celery import states
from celery.result import AsyncResult
from services import get_service
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)


# 任务状态存储（内存中，生产环境应使用Redis或数据库）
_task_progress = {}


def _update_progress(task_id: str, progress: int, message: str = ""):
    """更新任务进度"""
    _task_progress[task_id] = {
        'progress': progress,
        'message': message,
        'updated_at': datetime.now().isoformat()
    }


def get_task_status(task_id: str) -> Optional[Dict[str, Any]]:
    """获取任务状态和进度"""
    try:
        # 获取Celery任务结果
        result = AsyncResult(task_id, app=celery_app)
        
        # 构建状态信息
        status_info = {
            'task_id': task_id,
            'state': result.state,
            'progress': 0,
            'message': ''
        }
        
        # 获取进度信息
        if task_id in _task_progress:
            progress_info = _task_progress[task_id]
            status_info['progress'] = progress_info.get('progress', 0)
            status_info['message'] = progress_info.get('message', '')
        
        # 如果任务完成，返回结果
        if result.state == states.SUCCESS:
            status_info['result'] = result.result
            # 清理进度缓存
            if task_id in _task_progress:
                del _task_progress[task_id]
                
        elif result.state == states.FAILURE:
            status_info['error'] = str(result.result)
            if task_id in _task_progress:
                del _task_progress[task_id]
        
        return status_info
        
    except Exception as e:
        logger.error(f"获取任务状态失败: {e}")
        return None


@celery_app.task(bind=True, max_retries=3)
def recognize_vehicle_task(self, image_path: str, user_id: Optional[int] = None, 
                          image_filename: Optional[str] = None) -> Dict[str, Any]:
    """
    车辆识别异步任务
    
    Args:
        image_path: 图片路径
        user_id: 用户ID（可选）
        image_filename: 图片文件名（可选）
    
    Returns:
        Dict: 识别结果
    """
    task_id = self.request.id
    logger.info(f"开始识别任务: {task_id}, 图片: {image_path}")
    
    # 更新任务状态为处理中
    self.update_state(
        state=states.STARTED,
        meta={'progress': 0, 'message': '开始识别...'}
    )
    _update_progress(task_id, 0, '开始识别...')
    
    try:
        # 获取模型服务
        service = get_service()
        
        # 进度回调函数
        def progress_callback(t_id: str, progress: int, message: str):
            _update_progress(task_id, progress, message)
            # 更新Celery状态
            self.update_state(
                state=states.STARTED,
                meta={'progress': progress, 'message': message}
            )
        
        # 执行识别
        results = service.recognize(
            image_path, 
            task_id=task_id,
            progress_callback=progress_callback
        )
        
        if not results:
            logger.warning(f"任务 {task_id} 未识别到车辆")
            return {
                'success': False,
                'message': '未识别到车辆',
                'vehicles': []
            }
        
        # 构建结果
        result_data = {
            'success': True,
            'vehicles': [r.to_dict() for r in results],
            'count': len(results),
            'image_filename': image_filename
        }
        
        # 保存到数据库（如果用户已登录）
        if user_id:
            _save_to_history(user_id, image_filename, results)
        
        logger.info(f"识别任务完成: {task_id}, 识别到 {len(results)} 辆车")
        _update_progress(task_id, 100, '识别完成')
        
        return result_data
        
    except Exception as exc:
        logger.error(f"识别任务失败: {task_id}, 错误: {exc}")
        
        # 重试机制
        if self.request.retries < self.max_retries:
            logger.info(f"任务 {task_id} 将在 5 秒后重试...")
            raise self.retry(exc=exc, countdown=5)
        
        _update_progress(task_id, 0, f'识别失败: {str(exc)}')
        
        return {
            'success': False,
            'message': f'识别失败: {str(exc)}',
            'vehicles': []
        }


def _save_to_history(user_id: int, image_filename: Optional[str], 
                    results: list) -> None:
    """保存识别结果到历史记录"""
    try:
        import sys
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        from models.db import CarDatabase
        
        db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'car_recognition.db')
        db_client = CarDatabase(db_path)
        
        for result in results:
            db_client.insert_history(
                user_id=user_id,
                brand=result.brand,
                model=result.model,
                color=result.color,
                confidence=result.confidence,
                image_filename=image_filename or '',
                bbox=json.dumps(result.bbox) if result.bbox else None,
                price=result.purchase_advice.get('price') if result.purchase_advice else None,
                experience=result.purchase_advice.get('experience') if result.purchase_advice else None,
                pros_cons=result.purchase_advice.get('pros_cons') if result.purchase_advice else None,
                rating=result.purchase_advice.get('rating') if result.purchase_advice else None
            )
        
        logger.info(f"已保存 {len(results)} 条历史记录到数据库")
        
    except Exception as e:
        logger.error(f"保存历史记录失败: {e}")