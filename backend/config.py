import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 项目根目录
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ==========================================
# 环境配置
# ==========================================
ENV = os.getenv('ENV', 'development')
DEBUG = os.getenv('DEBUG', 'True').lower() in ('true', '1', 'yes')
SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-here')

# ==========================================
# 数据库配置
# ==========================================
DATABASE_URL = os.getenv('DATABASE_URL', f'sqlite:///{os.path.join(BASE_DIR, "car_recognition.db")}')

# ==========================================
# 文件存储配置
# ==========================================
STORAGE_TYPE = os.getenv('STORAGE_TYPE', 'local')
UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', os.path.join(BASE_DIR, 'uploads'))
MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10MB

# ==========================================
# AI模型服务配置
# ==========================================
MODEL_SERVICE_TYPE = os.getenv('MODEL_SERVICE_TYPE', 'ollama')

# Ollama配置
OLLAMA_HOST = os.getenv('OLLAMA_HOST', 'http://localhost:11434')
OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'qwen3-vl:8b')
OLLAMA_TIMEOUT = int(os.getenv('OLLAMA_TIMEOUT', '300'))

# vLLM配置
VLLM_HOST = os.getenv('VLLM_HOST', 'http://localhost:8000')
VLLM_MODEL = os.getenv('VLLM_MODEL', 'qwen3-vl:8b')
VLLM_TIMEOUT = int(os.getenv('VLLM_TIMEOUT', '300'))

# ==========================================
# Celery配置
# ==========================================
CELERY_BROKER_TYPE = os.getenv('CELERY_BROKER_TYPE', 'sqlalchemy')
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = os.getenv('REDIS_PORT', '6379')
REDIS_DB = os.getenv('REDIS_DB', '0')
WORKER_CONCURRENCY = int(os.getenv('WORKER_CONCURRENCY', '1'))

# ==========================================
# S3配置
# ==========================================
S3_BUCKET = os.getenv('S3_BUCKET', '')
S3_REGION = os.getenv('S3_REGION', 'us-east-1')
S3_ACCESS_KEY = os.getenv('S3_ACCESS_KEY', '')
S3_SECRET_KEY = os.getenv('S3_SECRET_KEY', '')
S3_ENDPOINT = os.getenv('S3_ENDPOINT', 'https://s3.amazonaws.com')

# ==========================================
# 阿里云OSS配置
# ==========================================
OSS_BUCKET = os.getenv('OSS_BUCKET', '')
OSS_REGION = os.getenv('OSS_REGION', 'oss-cn-hangzhou')
OSS_ACCESS_KEY_ID = os.getenv('OSS_ACCESS_KEY_ID', '')
OSS_ACCESS_KEY_SECRET = os.getenv('OSS_ACCESS_KEY_SECRET', '')
OSS_ENDPOINT = os.getenv('OSS_ENDPOINT', 'https://oss-cn-hangzhou.aliyuncs.com')

# ==========================================
# Flask配置字典
# ==========================================
FLASK_CONFIG = {
    'SECRET_KEY': SECRET_KEY,
    'UPLOAD_FOLDER': UPLOAD_FOLDER,
    'MAX_CONTENT_LENGTH': MAX_CONTENT_LENGTH,
    'DEBUG': DEBUG
}

# ==========================================
# 日志配置
# ==========================================
LOG_LEVEL = os.getenv('LOG_LEVEL', 'DEBUG')
LOGGING_CONFIG = {
    'level': LOG_LEVEL,
    'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
}

# ==========================================
# 获取数据库路径（兼容旧代码）
# ==========================================
def get_database_path():
    """获取SQLite数据库文件路径"""
    if DATABASE_URL.startswith('sqlite:///'):
        return DATABASE_URL.replace('sqlite:///', '')
    return os.path.join(BASE_DIR, 'car_recognition.db')