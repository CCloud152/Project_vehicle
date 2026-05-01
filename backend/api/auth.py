import os
import logging
import re
from flask import Blueprint, request, g
from models.user import UserModel
from utils.auth import JWTManager, jwt_required, get_current_user_id
from utils.response import success_response, error_response

logger = logging.getLogger(__name__)

# 创建蓝图
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

# 初始化JWT管理器（密钥从环境变量或配置文件获取）
JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'your-secret-key-change-in-production')
JWT_EXPIRE_HOURS = int(os.environ.get('JWT_EXPIRE_HOURS', '24'))

jwt_manager = JWTManager(
    secret_key=JWT_SECRET_KEY,
    access_token_expire=JWT_EXPIRE_HOURS
)

# 初始化用户模型
db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'car_recognition.db')
user_model = UserModel(db_path)


def validate_username(username):
    """验证用户名格式"""
    if not username or len(username) < 3 or len(username) > 20:
        return False, "用户名长度应为3-20个字符"
    
    # 只允许字母、数字、下划线
    if not re.match(r'^[a-zA-Z0-9_]+$', username):
        return False, "用户名只能包含字母、数字和下划线"
    
    return True, None


def validate_password(password):
    """验证密码强度"""
    if not password or len(password) < 6:
        return False, "密码长度至少为6个字符"
    
    if len(password) > 128:
        return False, "密码长度不能超过128个字符"
    
    return True, None


def validate_email(email):
    """验证邮箱格式"""
    if not email:
        return True, None  # 邮箱可选
    
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, email):
        return False, "邮箱格式不正确"
    
    return True, None


@auth_bp.route('/register', methods=['POST'])
def register():
    """用户注册"""
    try:
        data = request.get_json()
        
        if not data:
            return error_response('请求数据格式错误')
        
        username = data.get('username', '').strip()
        password = data.get('password', '')
        email = data.get('email', '').strip() or None
        
        # 验证用户名
        valid, msg = validate_username(username)
        if not valid:
            return error_response(msg)
        
        # 验证密码
        valid, msg = validate_password(password)
        if not valid:
            return error_response(msg)
        
        # 验证邮箱
        valid, msg = validate_email(email)
        if not valid:
            return error_response(msg)
        
        # 创建用户
        user = user_model.create_user(username, password, email)
        
        if not user:
            return error_response('用户名或邮箱已被注册')
        
        logger.info(f"新用户注册成功: {username}")
        
        # 生成token
        tokens = jwt_manager.generate_tokens(user['id'], user['username'])
        
        return success_response({
            'user': {
                'id': user['id'],
                'username': user['username'],
                'email': user['email'],
                'created_at': user['created_at']
            },
            'token': tokens
        }, '注册成功')
        
    except Exception as e:
        logger.error(f"注册失败: {e}")
        return error_response(f'注册失败: {str(e)}', 500)


@auth_bp.route('/login', methods=['POST'])
def login():
    """用户登录"""
    try:
        data = request.get_json()
        
        if not data:
            return error_response('请求数据格式错误')
        
        username = data.get('username', '').strip()
        password = data.get('password', '')
        
        if not username or not password:
            return error_response('用户名和密码不能为空')
        
        # 验证用户
        user = user_model.verify_password(username, password)
        
        if not user:
            return error_response('用户名或密码错误', 401)
        
        logger.info(f"用户登录成功: {username}")
        
        # 生成token
        tokens = jwt_manager.generate_tokens(user['id'], user['username'])
        
        return success_response({
            'user': {
                'id': user['id'],
                'username': user['username'],
                'email': user['email'],
                'avatar_url': user.get('avatar_url'),
                'created_at': user['created_at'],
                'last_login_at': user.get('last_login_at')
            },
            'token': tokens
        }, '登录成功')
        
    except Exception as e:
        logger.error(f"登录失败: {e}")
        return error_response(f'登录失败: {str(e)}', 500)


@auth_bp.route('/logout', methods=['POST'])
@jwt_required(jwt_manager, user_model)
def logout():
    """用户登出"""
    try:
        # 获取当前token
        token = jwt_manager.get_token_from_header()
        
        if token:
            # 将token加入黑名单（使其失效）
            payload = jwt_manager.decode_token(token)
            if payload and 'exp' in payload:
                from datetime import datetime
                expires_at = datetime.utcfromtimestamp(payload['exp']).isoformat()
                user_model.add_token_to_blacklist(token, expires_at)
                logger.info(f"用户登出，token加入黑名单: {g.username}")
        
        return success_response({}, '登出成功')
        
    except Exception as e:
        logger.error(f"登出失败: {e}")
        return error_response(f'登出失败: {str(e)}', 500)


@auth_bp.route('/profile', methods=['GET'])
@jwt_required(jwt_manager, user_model)
def get_profile():
    """获取当前用户信息"""
    try:
        user_id = get_current_user_id()
        user = user_model.get_user_by_id(user_id)
        
        if not user:
            return error_response('用户不存在', 404)
        
        return success_response({
            'user': {
                'id': user['id'],
                'username': user['username'],
                'email': user['email'],
                'avatar_url': user.get('avatar_url'),
                'created_at': user['created_at'],
                'last_login_at': user.get('last_login_at')
            }
        }, '获取成功')
        
    except Exception as e:
        logger.error(f"获取用户信息失败: {e}")
        return error_response(f'获取失败: {str(e)}', 500)


@auth_bp.route('/profile', methods=['PUT'])
@jwt_required(jwt_manager, user_model)
def update_profile():
    """更新用户信息"""
    try:
        data = request.get_json()
        
        if not data:
            return error_response('请求数据格式错误')
        
        user_id = get_current_user_id()
        
        # 只允许更新特定字段
        allowed_fields = {}
        if 'email' in data:
            valid, msg = validate_email(data['email'])
            if not valid:
                return error_response(msg)
            allowed_fields['email'] = data['email']
        
        if 'avatar_url' in data:
            allowed_fields['avatar_url'] = data['avatar_url']
        
        if not allowed_fields:
            return error_response('没有可更新的字段')
        
        success = user_model.update_user(user_id, **allowed_fields)
        
        if success:
            logger.info(f"用户信息更新成功: {g.username}")
            return success_response({}, '更新成功')
        else:
            return error_response('更新失败')
        
    except Exception as e:
        logger.error(f"更新用户信息失败: {e}")
        return error_response(f'更新失败: {str(e)}', 500)


@auth_bp.route('/change-password', methods=['POST'])
@jwt_required(jwt_manager, user_model)
def change_password():
    """修改密码"""
    try:
        data = request.get_json()
        
        if not data:
            return error_response('请求数据格式错误')
        
        old_password = data.get('old_password', '')
        new_password = data.get('new_password', '')
        
        if not old_password or not new_password:
            return error_response('原密码和新密码不能为空')
        
        # 验证新密码强度
        valid, msg = validate_password(new_password)
        if not valid:
            return error_response(msg)
        
        user_id = get_current_user_id()
        success, message = user_model.change_password(user_id, old_password, new_password)
        
        if success:
            logger.info(f"用户修改密码成功: {g.username}")
            return success_response({}, message)
        else:
            return error_response(message, 400)
        
    except Exception as e:
        logger.error(f"修改密码失败: {e}")
        return error_response(f'修改失败: {str(e)}', 500)


@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(jwt_manager)
def refresh_token():
    """刷新Token（延长有效期）"""
    try:
        user_id = get_current_user_id()
        username = g.username
        
        # 生成新的token
        tokens = jwt_manager.generate_tokens(user_id, username)
        
        return success_response({
            'token': tokens
        }, '刷新成功')
        
    except Exception as e:
        logger.error(f"刷新token失败: {e}")
        return error_response(f'刷新失败: {str(e)}', 500)


# 导出jwt_manager供其他模块使用
__all__ = ['auth_bp', 'jwt_manager', 'user_model']