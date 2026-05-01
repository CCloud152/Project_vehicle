import os
import logging
from flask import Blueprint, request, jsonify, g
from models.db import CarDatabase
from utils.response import success_response, error_response
from utils.auth import jwt_required, get_current_user_id
from api.auth import jwt_manager

logger = logging.getLogger(__name__)

# 创建蓝图
history_bp = Blueprint('history', __name__, url_prefix='/history')

# 初始化数据库客户端
db_client = CarDatabase(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'car_recognition.db'))


@history_bp.route('/', methods=['GET'])
@jwt_required(jwt_manager)
def get_history():
    """获取当前用户的历史记录列表"""
    try:
        limit = request.args.get('limit', 100, type=int)
        user_id = get_current_user_id()
        
        # 只查询当前用户的历史记录
        records = db_client.get_history_records(limit=limit, user_id=user_id)

        return success_response({
            'records': records,
            'count': len(records)
        }, '获取历史记录成功')
    except Exception as e:
        logger.error(f"获取历史记录失败: {e}")
        return error_response(f'查询失败: {str(e)}', 500)


@history_bp.route('/<int:record_id>', methods=['GET'])
@jwt_required(jwt_manager)
def get_history_detail(record_id):
    """获取历史记录详情（带权限检查）"""
    try:
        user_id = get_current_user_id()
        
        # 使用带权限检查的方法查询
        record = db_client.get_history_by_id_with_permission(record_id, user_id=user_id)
        
        if not record:
            return error_response('记录不存在或无权限查看', 404)

        # 构建购买建议（从历史记录中提取）
        purchase_advice = {
            'price': record.get('price', '暂无'),
            'experience': record.get('experience', '暂无'),
            'pros_cons': record.get('pros_cons', '暂无'),
            'rating': record.get('rating', '★☆☆☆☆'),
            'official_url': ''
        }

        return success_response({
            'record': record,
            'purchase_advice': purchase_advice
        }, '获取历史记录详情成功')

    except Exception as e:
        logger.error(f"获取历史记录详情失败: {e}")
        return error_response(f'查询失败: {str(e)}', 500)


@history_bp.route('/<int:record_id>', methods=['DELETE'])
@jwt_required(jwt_manager)
def delete_history(record_id):
    """删除历史记录（只能删除自己的）"""
    try:
        user_id = get_current_user_id()
        
        # 只能删除自己的记录
        result = db_client.delete_history_by_id(record_id, user_id=user_id)
        
        if not result['success']:
            return error_response('记录不存在或您无权删除', 404)

        logger.info(f"用户 {g.username} 删除历史记录: {record_id}")
        return success_response({}, '删除成功')
    except Exception as e:
        logger.error(f"删除历史记录失败: {e}")
        return error_response(f'删除失败: {str(e)}', 500)


@history_bp.route('/stats', methods=['GET'])
@jwt_required(jwt_manager)
def get_history_stats():
    """获取用户识别统计信息"""
    try:
        user_id = get_current_user_id()
        
        # 获取用户的历史记录
        records = db_client.get_history_records(limit=1000, user_id=user_id)
        
        # 统计信息
        total_count = len(records)
        unique_brands = set()
        unique_models = set()
        
        for record in records:
            if record.get('brand'):
                unique_brands.add(record['brand'])
            if record.get('model'):
                unique_models.add(record['model'])
        
        return success_response({
            'total_recognitions': total_count,
            'unique_brands': len(unique_brands),
            'unique_models': len(unique_models),
            'brand_list': list(unique_brands)[:10]  # 最多返回10个品牌
        }, '获取统计信息成功')
        
    except Exception as e:
        logger.error(f"获取统计信息失败: {e}")
        return error_response(f'获取失败: {str(e)}', 500)
