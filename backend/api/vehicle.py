import os
import uuid
import json
import logging
from flask import Blueprint, request, jsonify, send_from_directory, g
from werkzeug.utils import secure_filename
import config
from services.ollama_client import OllamaClient
from models.db import CarDatabase
from utils.image_processor import allowed_file, validate_image
from utils.response import success_response, error_response
from utils.auth import optional_auth, get_current_user_id
from api.auth import jwt_manager

# 导入配置
UPLOAD_FOLDER = config.UPLOAD_FOLDER

logger = logging.getLogger(__name__)

# 创建蓝图
vehicle_bp = Blueprint('vehicle', __name__)

# 初始化服务
ollama_client = OllamaClient('qwen3-vl:8b')
db_client = CarDatabase(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'car_recognition.db'))

# 确保上传目录存在
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


@vehicle_bp.route('/upload', methods=['POST'])
def upload_image():
    """上传图片"""
    if 'file' not in request.files:
        return error_response('未选择图片')

    file = request.files['file']
    if file.filename == '':
        return error_response('未选择图片')

    if not allowed_file(file.filename):
        return error_response('不支持的图片格式')

    try:
        # 获取安全的文件名
        original_filename = secure_filename(file.filename)
        file_ext = original_filename.rsplit('.', 1)[-1].lower()

        # 生成唯一文件名
        filename = f"{uuid.uuid4().hex}.{file_ext}"
        save_path = os.path.join(UPLOAD_FOLDER, filename)

        # 保存文件
        file.save(save_path)

        # 验证文件确实保存了
        if os.path.exists(save_path) and os.path.getsize(save_path) > 0:
            logger.info(f"文件保存成功: {filename} ({os.path.getsize(save_path)} bytes)")
            return success_response({'filename': filename}, '图片上传成功')
        else:
            return error_response('文件保存失败')

    except Exception as e:
        logger.error(f"上传失败: {e}")
        return error_response(f'上传失败: {str(e)}', 500)


@vehicle_bp.route('/recognize', methods=['POST'])
@optional_auth(jwt_manager)
def recognize_vehicle():
    """识别车辆"""
    data = request.get_json()
    if not data:
        return error_response('请求数据格式错误')

    filename = data.get('filename')
    if not filename:
        return error_response('缺少图片文件名')

    image_path = os.path.join(UPLOAD_FOLDER, filename)
    if not os.path.exists(image_path):
        return error_response('图片不存在', 404)

    # 验证图片
    is_valid, msg = validate_image(image_path)
    if not is_valid:
        return error_response(msg)

    try:
        # 调用Ollama模型识别车辆
        vehicles_info = ollama_client.recognize_vehicle(image_path)
        if not vehicles_info:
            return error_response('识别失败，未检测到车辆')

        if not isinstance(vehicles_info, list):
            vehicles_info = [vehicles_info]

        # 获取当前用户ID（可能为None，表示未登录）
        user_id = get_current_user_id()

        # 处理每辆车的信息
        result_vehicles = []
        for vehicle in vehicles_info:
            brand = vehicle.get('brand', '未知')
            model = vehicle.get('model', '未知')
            color = vehicle.get('color', '未知')
            confidence = vehicle.get('confidence', 0.0)
            bbox = vehicle.get('bbox', {})

            # 生成购买建议
            purchase_advice = ollama_client.get_purchase_advice(brand, model)

            result_vehicles.append({
                'basic': {
                    'brand': brand,
                    'model': model,
                    'color': color,
                    'confidence': float(confidence)
                },
                'purchase_advice': purchase_advice,
                'bbox': bbox
            })

            # 保存到数据库（如果用户已登录，关联到用户）
            db_client.insert_history(
                user_id=user_id,  # 新增：关联用户ID
                brand=brand,
                model=model,
                color=color,
                confidence=confidence,
                image_filename=filename,
                bbox=json.dumps(bbox) if bbox else None,
                price=purchase_advice.get('price'),
                experience=purchase_advice.get('experience'),
                pros_cons=purchase_advice.get('pros_cons'),
                rating=purchase_advice.get('rating')
            )

        # 记录识别日志
        if user_id:
            logger.info(f"用户 {g.username} 识别成功: {len(result_vehicles)}辆车")
        else:
            logger.info(f"匿名用户识别成功: {len(result_vehicles)}辆车")

        return success_response({
            'vehicles': result_vehicles,
            'image_filename': filename
        }, f'识别完成，共{len(result_vehicles)}辆车')

    except Exception as e:
        logger.error(f"识别失败: {str(e)}")
        return error_response(f'识别失败: {str(e)}', 500)


@vehicle_bp.route('/uploads/<filename>')
def serve_uploaded_file(filename):
    """提供上传文件的访问"""
    return send_from_directory(UPLOAD_FOLDER, filename)


@vehicle_bp.route('/health', methods=['GET'])
def health_check():
    """健康检查"""
    return success_response({'status': 'healthy'}, '服务正常')
