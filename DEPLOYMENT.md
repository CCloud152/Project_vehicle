# 车辆识别系统 - 部署指南

## 架构说明

```
用户浏览器 → 本地Flask服务 → Celery Worker → 云端vLLM/Ollama
              (SQLite/Celery)    (任务队列)      (模型推理)
```

**职责分离：**
- **本地**：接收请求、管理任务、存储数据、返回结果
- **云端(AutoDL)**：只跑模型推理服务

## 快速开始（3步）

### 1. 云端部署vLLM（AutoDL）

SSH登录AutoDL实例，执行：

```bash
# 安装vLLM
pip install vllm==0.5.0

# 启动服务（OpenAI兼容API）
python -m vllm.entrypoints.openai.api_server \
    --model Qwen/Qwen3-VL-8B-Instruct \
    --host 0.0.0.0 \
    --port 8000 \
    --tensor-parallel-size 1
```

**控制台操作：**
- 开放8000端口
- 记录公网IP: `http://autodl-xxx.autodl.com:8000`

### 2. 本地配置

编辑 `Project_vehicle/.env`：

```bash
MODEL_SERVICE_TYPE=vllm
VLLM_HOST=http://autodl-xxx.autodl.com:8000
VLLM_MODEL=Qwen/Qwen3-VL-8B-Instruct
```

### 3. 启动本地服务

```bash
cd Project_vehicle/backend

# 安装依赖（首次）
pip install -r requirements.txt

# 终端1：启动Celery Worker
celery -A celery_app worker --loglevel=info --concurrency=1

# 终端2：启动Flask
python app.py
```

访问：`http://localhost:5000`

## 可选：本地Ollama（开发测试）

```bash
# 1. 安装并启动Ollama
ollama serve

# 2. 拉取模型
ollama pull qwen3-vl:8b

# 3. 配置.env
MODEL_SERVICE_TYPE=ollama
OLLAMA_HOST=http://localhost:11434

# 4. 启动服务（同上）
```

## 模型服务对比

| 方案 | 部署位置 | 适用场景 | 配置 |
|------|---------|---------|------|
| **vLLM** | AutoDL云端 | 生产环境 | `MODEL_SERVICE_TYPE=vllm`<br>`VLLM_HOST=http://autodl-ip:8000` |
| **Ollama** | 本地 | 开发测试 | `MODEL_SERVICE_TYPE=ollama`<br>`OLLAMA_HOST=http://localhost:11434` |

**接口完全同构**，切换只需改`.env`。

## 验证部署

```bash
# 测试vLLM服务
curl http://autodl-xxx:8000/health

# 测试本地服务
curl http://localhost:5000/health
```

## 核心文件说明

| 文件 | 职责 |
|------|------|
| `services/__init__.py` | 模型服务工厂，根据`MODEL_SERVICE_TYPE`创建实例 |
| `services/vllm_service.py` | vLLM客户端（HTTP调用） |
| `services/ollama_service.py` | Ollama客户端（库调用） |
| `tasks/recognition.py` | Celery任务，调用模型服务 |
| `api/async_recognition.py` | API路由，提交/查询任务 |