"""
异步识别API
支持提交异步任务、查询任务状态
"""

import os
import uuid
import logging
from flask import Blueprint, request, g
from celery.result import AsyncResult

from utils.response import success_response, error_response
from utils.auth import jwt_required, get_current_user_id, optional_auth
from api.auth import jwt_manager
from tasks.recognition import recognize_vehicle_task, get_task_status
from celery_app import celery_app

logger = logging.getLogger(__name__)

# 创建蓝图
async_bp = Blueprint('async', __name__, url_prefix='/async')

# 导入配置
import config
UPLOAD_FOLDER = config.UPLOAD_FOLDER


@async_bp.route('/recognize', methods=['POST'])
@optional_auth(jwt_manager)
def submit_recognition_task():
    """提交异步识别任务"""
    try:
        data = request.get_json()
        
        if not data:
            return error_response('请求数据格式错误')
        
        filename = data.get('filename')
        if not filename:
            return error_response('缺少图片文件名')
        
        image_path = os.path.join(UPLOAD_FOLDER, filename)
        if not os.path.exists(image_path):
            return error_response('图片不存在', 404)
        
        # 获取当前用户ID（可能为None）
        user_id = get_current_user_id()
        
        # 生成任务ID（可选，让Celery自动生成）
        # 提交异步任务
        logger.info(f"提交异步识别任务: {filename}, 用户: {user_id}")
        
        task = recognize_vehicle_task.delay(
            image_path=image_path,
            user_id=user_id,
            image_filename=filename
        )
        
        task_id = task.id
        
        logger.info(f"任务已提交: {task_id}")
        
        return success_response({
            'task_id': task_id,
            'status': 'pending',
            'message': '识别任务已提交，请通过任务ID查询进度'
        }, '任务提交成功')
        
    except Exception as e:
        logger.error(f"提交识别任务失败: {e}")
        return error_response(f'提交失败: {str(e)}', 500)


@async_bp.route('/tasks/<task_id>', methods=['GET'])
def get_task_info(task_id):
    """获取任务状态和结果"""
    try:
        # 获取任务状态
        status_info = get_task_status(task_id)
        
        if not status_info:
            return error_response('任务不存在', 404)
        
        return success_response(status_info, '获取任务状态成功')
        
    except Exception as e:
        logger.error(f"获取任务状态失败: {e}")
        return error_response(f'查询失败: {str(e)}', 500)


@async_bp.route('/tasks/<task_id>/progress', methods=['GET'])
def get_task_progress(task_id):
    """获取任务进度（简化接口）"""
    try:
        status_info = get_task_status(task_id)
        
        if not status_info:
            return error_response('任务不存在', 404)
        
        # 只返回进度相关信息
        progress_info = {
            'task_id': task_id,
            'state': status_info.get('state'),
            'progress': status_info.get('progress', 0),
            'message': status_info.get('message', '')
        }
        
        return success_response(progress_info, '获取进度成功')
        
    except Exception as e:
        logger.error(f"获取任务进度失败: {e}")
        return error_response(f'查询失败: {str(e)}', 500)


@async_bp.route('/tasks/<task_id>/cancel', methods=['POST'])
@jwt_required(jwt_manager)
def cancel_task(task_id):
    """取消任务（只能取消自己的任务）"""
    try:
        # 获取任务信息
        result = AsyncResult(task_id, app=celery_app)
        
        # 检查任务是否存在
        if not result:
            return error_response('任务不存在', 404)
        
        # 检查任务是否已完成
        if result.ready():
            return error_response('任务已完成，无法取消', 400)
        
        # 取消任务
        result.revoke(terminate=True)
        
        logger.info(f"任务已取消: {task_id}")
        
        return success_response({}, '任务已取消')
        
    except Exception as e:
        logger.error(f"取消任务失败: {e}")
        return error_response(f'取消失败: {str(e)}', 500)


@async_bp.route('/tasks', methods=['GET'])
@jwt_required(jwt_manager)
def list_user_tasks():
    """获取当前用户的任务列表（需要Redis，SQLite不支持）"""
    # 注意：SQLite作为Broker时，无法查询历史任务
    # 这个功能需要Redis支持
    
    return error_response('当前配置不支持查询任务列表，请使用任务ID查询单个任务状态', 501)