from flask import Blueprint
from api.vehicle import vehicle_bp
from api.history import history_bp
from api.auth import auth_bp
from api.async_recognition import async_bp

# 创建主API蓝图
api_bp = Blueprint('api', __name__, url_prefix='/api')

# 注册子蓝图
api_bp.register_blueprint(vehicle_bp)
api_bp.register_blueprint(history_bp)
api_bp.register_blueprint(auth_bp)
api_bp.register_blueprint(async_bp)
