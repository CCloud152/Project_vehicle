# 车辆识别系统部署指南

## 架构概览

```
┌─────────────────┐      HTTP/WebSocket      ┌─────────────────┐
│   用户浏览器     │  ←────────────────────→  │  Flask后端      │
│  (手机/PC)      │                          │  (本地/轻量云)   │
└─────────────────┘                          └────────┬────────┘
                                                      │
                           ┌─────────────────────────┘
                           │ Celery + SQLite/Redis
                           │ (异步任务队列)
                           ↓
                    ┌─────────────────┐
                    │  Celery Worker  │
                    │  (执行识别任务)  │
                    └────────┬────────┘
                             │
                    ┌────────┴────────┐
                    │                 │
              ┌─────▼─────┐     ┌─────▼─────┐
              │ Ollama    │     │ vLLM      │
              │ (本地GPU) │     │ (云端GPU) │
              └───────────┘     └───────────┘
```

---

## 方案A：本地开发（当前配置）

### 1. 环境准备

```bash
# 进入项目目录
cd /path/to/RemakeV3_3_1

# 激活虚拟环境
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac

# 安装依赖
pip install -r backend/requirements.txt
```

### 2. 配置（使用Mock模式，无需Ollama）

```bash
# Windows PowerShell
$env:INFERENCE_BACKEND="mock"
$env:MOCK_DELAY="2.0"

# Linux/Mac
export INFERENCE_BACKEND=mock
export MOCK_DELAY=2.0
```

### 3. 启动服务

**终端1：启动Flask应用**
```bash
cd backend
python app.py
```

**终端2：启动Celery Worker**
```bash
cd backend
celery -A celery_app worker --loglevel=info
```

### 4. 测试

```bash
# 1. 上传图片
curl -X POST -F "file=@test.jpg" http://localhost:5000/api/upload

# 2. 提交异步识别任务
curl -X POST http://localhost:5000/api/async/recognize \
  -H "Content-Type: application/json" \
  -d "{\"filename\":\"xxx.jpg\"}"

# 3. 查询任务状态
curl http://localhost:5000/api/async/tasks/{task_id}
```

---

## 方案B：本地Ollama

### 1. 安装Ollama

```bash
# Windows/Mac: 下载安装包 https://ollama.com
# Linux:
curl -fsSL https://ollama.com/install.sh | sh
```

### 2. 下载模型

```bash
ollama pull qwen3-vl:8b
```

### 3. 配置

```bash
export INFERENCE_BACKEND=ollama
export OLLAMA_MODEL=qwen3-vl:8b
```

### 4. 启动（同方案A）

---

## 方案C：云端vLLM（推荐生产环境）

### 1. 云端GPU服务器部署

在AutoDL/阿里云等云平台创建GPU实例（RTX 3090 / A100）

**上传并运行部署脚本：**
```bash
# 上传脚本到云端服务器
scp backend/scripts/deploy_vllm.sh root@your-server-ip:/root/

# SSH登录
ssh root@your-server-ip

# 运行部署脚本
chmod +x deploy_vllm.sh
./deploy_vllm.sh
```

### 2. 本地Flask配置

```bash
# 配置指向云端vLLM
export INFERENCE_BACKEND=vllm
export VLLM_API_URL=http://your-server-ip:8000/v1
export VLLM_API_KEY=your-api-key  # 如果设置了
```

### 3. 启动Flask + Celery（同方案A）

---

## Celery配置切换

### 开发阶段（SQLite，零配置）
```bash
export CELERY_BROKER_TYPE=sqlalchemy
# 无需安装Redis
```

### 生产阶段（Redis）
```bash
# 安装Redis（Ubuntu）
sudo apt update
sudo apt install redis-server
sudo systemctl start redis

# 配置
export CELERY_BROKER_TYPE=redis
export REDIS_HOST=localhost
export REDIS_PORT=6379
```

---

## API文档

### 同步识别（旧接口，保留兼容）
```
POST /api/recognize
Body: {"filename": "xxx.jpg"}
```

### 异步识别（新接口，推荐）
```
# 提交任务
POST /api/async/recognize
Body: {"filename": "xxx.jpg"}
Response: {"task_id": "xxx", "status": "pending"}

# 查询状态
GET /api/async/tasks/{task_id}
Response: {
  "task_id": "xxx",
  "state": "processing",  // pending/processing/completed/failed
  "progress": 50,
  "message": "分析图片...",
  "result": {...}  // 完成后
}

# WebSocket实时进度
ws://localhost:5000/socket.io/
Event: join_task {task_id: "xxx"}
Receive: task_progress {progress: 50, message: "..."}
```

---

## 环境变量汇总

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `INFERENCE_BACKEND` | 推理后端类型 | `ollama` |
| `OLLAMA_MODEL` | Ollama模型名 | `qwen3-vl:8b` |
| `VLLM_API_URL` | vLLM API地址 | - |
| `VLLM_API_KEY` | vLLM API密钥 | - |
| `VLLM_MODEL` | vLLM模型名 | `qwen3-vl:8b` |
| `MOCK_DELAY` | Mock延迟(秒) | `2.0` |
| `CELERY_BROKER_TYPE` | Celery Broker类型 | `sqlalchemy` |
| `REDIS_HOST` | Redis主机 | `localhost` |
| `REDIS_PORT` | Redis端口 | `6379` |

---

## 故障排查

### 1. Celery Worker无法启动
```bash
# 检查Broker URL
celery -A celery_app inspect ping

# 重置Celery（删除SQLite数据库）
rm celery_broker.db celery_results.db
```

### 2. WebSocket连接失败
```bash
# 检查Flask是否正确使用socketio.run()
# 确保async_mode='threading'
```

### 3. vLLM连接超时
```bash
# 检查防火墙
# 确保端口8000开放
sudo ufw allow 8000
```

### 4. GPU显存不足
```bash
# 降低batch size或模型大小
# vLLM参数调整：
--gpu-memory-utilization 0.7  # 降低显存使用
--max-model-len 2048          # 降低序列长度