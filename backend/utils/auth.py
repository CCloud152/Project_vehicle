import jwt
import logging
from datetime import datetime, timedelta
from functools import wraps
from flask import request, g, current_app

logger = logging.getLogger(__name__)


class JWTManager:
    """JWT认证管理器"""
    
    def __init__(self, secret_key, algorithm='HS256', access_token_expire=24):
        """
        初始化JWT管理器
        
        Args:
            secret_key: JWT密钥
            algorithm: 加密算法
            access_token_expire: 访问令牌过期时间（小时）
        """
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.access_token_expire = access_token_expire
    
    def generate_tokens(self, user_id, username, **extra_claims):
        """
        生成JWT Token
        
        Args:
            user_id: 用户ID
            username: 用户名
            **extra_claims: 额外声明
            
        Returns:
            dict: 包含access_token和过期时间的字典
        """
        now = datetime.utcnow()
        
        # Access Token
        access_payload = {
            'user_id': user_id,
            'username': username,
            'type': 'access',
            'iat': now,
            'exp': now + timedelta(hours=self.access_token_expire),
            **extra_claims
        }
        
        access_token = jwt.encode(
            access_payload,
            self.secret_key,
            algorithm=self.algorithm
        )
        
        return {
            'access_token': access_token,
            'token_type': 'Bearer',
            'expires_in': self.access_token_expire * 3600,  # 秒
            'expires_at': (now + timedelta(hours=self.access_token_expire)).isoformat()
        }
    
    def decode_token(self, token):
        """
        解码并验证Token
        
        Args:
            token: JWT Token
            
        Returns:
            dict: 解码后的payload，失败返回None
        """
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm]
            )
            
            # 验证token类型
            if payload.get('type') != 'access':
                logger.warning(f"无效的token类型: {payload.get('type')}")
                return None
            
            return payload
            
        except jwt.ExpiredSignatureError:
            logger.warning("Token已过期")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"无效的Token: {e}")
            return None
        except Exception as e:
            logger.error(f"解码Token失败: {e}")
            return None
    
    def get_token_from_header(self):
        """
        从请求头中提取Token
        
        Returns:
            str: Token字符串，未找到返回None
        """
        auth_header = request.headers.get('Authorization', '')
        
        # 支持 "Bearer <token>" 格式
        if auth_header.startswith('Bearer '):
            return auth_header[7:]
        
        # 支持直接传token
        if auth_header:
            return auth_header
        
        return None


def jwt_required(jwt_manager, user_model=None):
    """
    JWT认证装饰器
    
    Args:
        jwt_manager: JWTManager实例
        user_model: 用户模型实例（可选，用于加载完整用户信息）
        
    Returns:
        decorator: 装饰器函数
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # 获取token
            token = jwt_manager.get_token_from_header()
            
            if not token:
                return {
                    'status': 'error',
                    'message': '缺少认证信息，请先登录'
                }, 401
            
            # 解码token
            payload = jwt_manager.decode_token(token)
            
            if not payload:
                return {
                    'status': 'error',
                    'message': '认证信息无效或已过期，请重新登录'
                }, 401
            
            # 检查token是否在黑名单（用于登出）
            if user_model and hasattr(user_model, 'is_token_blacklisted'):
                if user_model.is_token_blacklisted(token):
                    return {
                        'status': 'error',
                        'message': '该登录已失效，请重新登录'
                    }, 401
            
            # 将用户信息存入g对象，供视图函数使用
            g.user_id = payload.get('user_id')
            g.username = payload.get('username')
            g.token_payload = payload
            
            # 如果提供了user_model，加载完整用户信息
            if user_model and hasattr(user_model, 'get_user_by_id'):
                g.current_user = user_model.get_user_by_id(g.user_id)
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator


def optional_auth(jwt_manager):
    """
    可选认证装饰器（不强制要求登录，但如果有token会解析用户信息）
    
    Args:
        jwt_manager: JWTManager实例
        
    Returns:
        decorator: 装饰器函数
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # 获取token
            token = jwt_manager.get_token_from_header()
            
            # 初始化默认值
            g.user_id = None
            g.username = None
            g.token_payload = None
            
            if token:
                # 尝试解码token
                payload = jwt_manager.decode_token(token)
                if payload:
                    g.user_id = payload.get('user_id')
                    g.username = payload.get('username')
                    g.token_payload = payload
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator


def get_current_user_id():
    """获取当前登录用户ID"""
    return getattr(g, 'user_id', None)


def get_current_username():
    """获取当前登录用户名"""
    return getattr(g, 'username', None)


def is_authenticated():
    """检查用户是否已认证"""
    return getattr(g, 'user_id', None) is not None