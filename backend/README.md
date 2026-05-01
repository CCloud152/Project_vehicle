# 车辆识别系统后端

## 阶段2.1完成：推理服务抽象层 + Celery配置

### 新增架构

```
backend/
├── services/              # 推理服务抽象层
│   ├── __init__.py        # 服务工厂（支持ollama/vllm/mock切换）
│   ├── base_service.py    # 抽象基类（统一接口）
│   ├── ollama_service.py  # Ollama本地实现
│   ├── vllm_service.py    # vLLM云端实现
│   └── mock_service.py    # Mock实现（开发测试用）
├── tasks/                 # Celery异步任务
│   ├── __init__.py
│   └── recognition.py     # 车辆识别异步任务
├── celery_app.py          # Celery配置（支持SQLite/Redis）
└── ...
```

### 配置切换推理后端

```bash
# 1. 本地Ollama（默认）
export INFERENCE_BACKEND=ollama
export OLLAMA_MODEL=qwen3-vl:8b

# 2. 云端vLLM
export INFERENCE_BACKEND=vllm
export VLLM_API_URL=http://your-gpu-server:8000/v1
export VLLM_API_KEY=your-api-key

# 3. Mock模式（前端开发测试用）
export INFERENCE_BACKEND=mock
export MOCK_DELAY=2.0  # 模拟延迟秒数
```

### Celery配置（零配置方案）

```bash
# 开发阶段（SQLite，无需安装Redis）
export CELERY_BROKER_TYPE=sqlalchemy

# 生产阶段（Redis）
export CELERY_BROKER_TYPE=redis
export REDIS_HOST=localhost
export REDIS_PORT=6379
```

### 启动服务

```bash
# 1. 启动Flask应用
.venv\Scripts\python backend\app.py

# 2. 启动Celery Worker（另一个终端）
.venv\Scripts\celery -A celery_app worker --loglevel=info

# 3. 启动Celery Beat（定时任务，可选）
.venv\Scripts\celery -A celery_app beat --loglevel=info
```

### 新API端点（阶段2.2准备）

```
POST /api/recognize/async      # 提交异步识别任务
GET  /api/tasks/{task_id}      # 查询任务状态
GET  /api/tasks/{task_id}/progress  # 查询任务进度
```

### 架构亮点

1. **工厂模式**：一行配置切换Ollama/vLLM/Mock
2. **零配置Celery**：SQLite作为Broker，无需安装Redis
3. **进度追踪**：支持实时进度回调（为WebSocket准备）
4. **统一接口**：所有后端实现相同的抽象基类

### 下一阶段（2.2）

- 改造recognize接口为异步
- 创建任务状态查询API
- 集成WebSocket实时进度推送