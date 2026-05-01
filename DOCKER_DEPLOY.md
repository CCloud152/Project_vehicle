# 车辆识别系统 - Docker部署指南

## 快速开始

### 1. 本地开发环境

```bash
# 进入项目目录
cd Project_vehicle

# 启动服务（使用SQLite作为broker，无需Redis）
docker-compose up -d
```

## vLLM云端部署（推荐生产环境）

### 架构说明

```
┌─────────────────────────────┐         ┌─────────────────────────────┐
│      本地/云服务器            │         │       AutoDL GPU实例         │
│  ┌─────────────────────┐    │         │  ┌─────────────────────┐    │
│  │   Flask后端服务      │    │  HTTP   │  │   vLLM服务          │    │
│  │   - 接收图片上传      │◄─────────────►│   - 模型推理          │    │
│  │   - Celery任务队列   │    │  8000   │  │   - OpenAI兼容API   │    │
│  │   - SQLite数据库     │    │         │  │   - qwen3-vl:8b     │    │
│  └─────────────────────┘    │         │  └─────────────────────┘    │
└─────────────────────────────┘         └─────────────────────────────┘
```

### 1. AutoDL端部署vLLM

```bash
# 进入项目目录
cd Project_vehicle/backend/scripts

# 运行部署脚本
chmod +x deploy_vllm_autodl.sh
./deploy_vllm_autodl.sh
```

**或手动部署：**

```bash
# 安装vLLM
pip install vllm==0.5.0

# 下载模型（如未下载）
modelscope download --model qwen/qwen3-vl-8b-instruct \
    --local_dir /root/autodl-tmp/qwen3-vl-8b

# 启动vLLM服务
python -m vllm.entrypoints.openai.api_server \
    --model /root/autodl-tmp/qwen3-vl-8b \
    --host 0.0.0.0 \
    --port 8000 \
    --gpu-memory-utilization 0.85 \
    --max-model-len 8192
```

### 2. 本地服务配置

编辑 `.env` 文件：

```bash
# 切换到vLLM服务
MODEL_SERVICE_TYPE=vllm

# vLLM云端地址（AutoDL提供的公网IP）
VLLM_HOST=http://autodl-xxx.autodl.com:8000
VLLM_MODEL=qwen3-vl:8b
VLLM_TIMEOUT=120

# 其他配置保持不变
CELERY_BROKER_TYPE=redis
REDIS_HOST=redis
```

### 3. 启动本地服务

```bash
docker-compose up -d
```

## Ollama部署（开发测试用）

### 方案A：本地Ollama

```bash
# 启动Ollama
ollama serve

# 拉取模型
ollama pull qwen3-vl:8b

# 配置.env
MODEL_SERVICE_TYPE=ollama
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=qwen3-vl:8b
```

### 方案B：远程Ollama（AutoDL）

```bash
# 在AutoDL上
ollama serve &

# 本地配置.env
MODEL_SERVICE_TYPE=ollama
OLLAMA_HOST=http://autodl-ip:11434
OLLAMA_MODEL=qwen3-vl:8b
```

## 环境变量配置

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `MODEL_SERVICE_TYPE` | 模型服务类型: ollama/vllm/mock | `ollama` |
| `OLLAMA_HOST` | Ollama服务地址 | `http://localhost:11434` |
| `OLLAMA_MODEL` | Ollama模型名 | `qwen3-vl:8b` |
| `VLLM_HOST` | vLLM服务地址 | `http://localhost:8000` |
| `VLLM_MODEL` | vLLM模型名 | `qwen3-vl:8b` |
| `VLLM_TIMEOUT` | vLLM超时时间 | `120` |
| `CELERY_BROKER_TYPE` | 消息队列: sqlalchemy/redis | `sqlalchemy` |
| `WORKER_CONCURRENCY` | Worker并发数 | `1` |

## 监控与日志

```bash
# 查看所有服务日志
docker-compose logs -f

# 查看特定服务日志
docker-compose logs -f backend
docker-compose logs -f celery_worker

# 查看Celery任务状态
docker-compose exec celery_worker celery -A celery_app inspect active

# 查看vLLM日志（AutoDL端）
tail -f vllm_server.log
```

## 常见问题

### Q: 容器无法连接到远程vLLM服务？
A: 检查以下几点：
1. AutoDL安全组是否开放8000端口
2. 本地能否ping通AutoDL公网IP
3. vLLM服务是否正常运行：`curl http://autodl-ip:8000/health`

### Q: 图片传输失败？
A: 检查vLLM服务配置：
- `max-model-len` 是否足够（建议8192）
- GPU显存是否充足
- 网络连接是否稳定

### Q: 如何切换模型服务？
A: 修改 `.env` 文件中的 `MODEL_SERVICE_TYPE`，然后重启：
```bash
docker-compose restart
```

## 架构对比

| 方案 | 适用场景 | 优点 | 缺点 |
|------|---------|------|------|
| **vLLM云端** | 生产环境 | 高性能、高并发、云端GPU | 需要网络连接 |
| **Ollama本地** | 开发测试 | 简单、离线可用 | 依赖本地GPU |
| **Ollama远程** | 共享GPU | 资源共享 | 需要内网穿透 |

## 完整部署架构（vLLM方案）

```
┌─────────────────────────────────────────────────────────┐
│                    前端 (HTML/JS)                        │
│              用户直接访问本地服务器                        │
└─────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│              Flask后端 (本地Docker)                      │
│         端口: 5000                                       │
│         - 文件上传、任务分发                              │
└─────────────────────────────────────────────────────────┘
                            │
            ┌───────────────┼───────────────┐
            ▼               ▼               ▼
     ┌──────────┐    ┌──────────┐    ┌──────────┐
     │  Redis   │    │  SQLite  │    │  vLLM    │
     │ (Broker) │    │ (数据库)  │    │ (云端GPU) │
     │  本地     │    │  本地     │    │  AutoDL   │
     └──────────┘    └──────────┘    └──────────┘
            │                              ▲
            ▼                              │
     ┌──────────┐                         │
     │  Celery  │    HTTP API调用          │
     │  Worker  │ ─────────────────────────┘
     │  本地     │    图片Base64传输
     └──────────┘