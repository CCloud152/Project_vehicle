import os
import logging
from flask import Flask, render_template, send_from_directory
from flask_cors import CORS
import config
from api.routes import api_bp
from websocket.events import init_socketio, socketio

# 导入配置
FLASK_CONFIG = config.FLASK_CONFIG
LOGGING_CONFIG = config.LOGGING_CONFIG
BASE_DIR = config.BASE_DIR

# 配置日志
logging.basicConfig(
    level=LOGGING_CONFIG['level'],
    format=LOGGING_CONFIG['format']
)
logger = logging.getLogger(__name__)

# 初始化Flask应用
app = Flask(__name__, static_folder=os.path.join(BASE_DIR, 'frontend'), template_folder=os.path.join(BASE_DIR, 'frontend'))

# 应用配置
app.config.update(FLASK_CONFIG)

# 启用CORS
CORS(app)

# 注册API蓝图
app.register_blueprint(api_bp)

# 初始化SocketIO
init_socketio(app)

# 静态文件路由
@app.route('/')
@app.route('/index')
def index():
    """主页面"""
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/history')
def history_page():
    """历史记录页面"""
    return send_from_directory(app.static_folder, 'history.html')

# 提供前端静态文件
@app.route('/<path:path>')
def serve_static(path):
    """提供静态文件"""
    return send_from_directory(app.static_folder, path)

# 健康检查
@app.route('/health')
def health_check():
    """健康检查"""
    return {'status': 'healthy'}

if __name__ == '__main__':
    # 打印所有路由
    print("=" * 50)
    print("可用路由:")
    for rule in app.url_map.iter_rules():
        print(f"{rule.endpoint}: {rule.rule} [{', '.join(rule.methods)}]")
    print("=" * 50)

    # 使用SocketIO启动应用
    socketio.run(
        app,
        host='0.0.0.0',
        port=5000,
        debug=FLASK_CONFIG['DEBUG'],
        allow_unsafe_werkzeug=True
    )
