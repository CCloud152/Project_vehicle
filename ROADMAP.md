# Project_vehicle 项目路线图

## 当前状态
**阶段3已完成** - vLLM云端部署支持

---

## 已完成阶段

### ✅ 阶段1：Linux迁移与基础修复（已完成）

- [x] Linux环境适配
- [x] Bug修复（权限、数据显示等）
- [x] 模型升级到 qwen3-vl:8b

### ✅ 阶段2：多用户并发测试（已完成）

- [x] Celery并发优化（worker_concurrency=1）
- [x] 任务超时配置（5分钟）
- [x] 错误重试机制（max_retries=3）

### ✅ 阶段3：云端部署准备（已完成）

- [x] vLLM服务支持（OpenAI兼容API）
- [x] 模型服务抽象（Ollama/vLLM同构接口）
- [x] 环境配置简化（.env文件）
- [x] 部署文档：`DEPLOYMENT.md`

---

## 架构说明

```
用户浏览器 → 本地Flask → Celery Worker → 云端vLLM（AutoDL）
              SQLite      任务队列        模型推理
```

**职责分离：**
- 本地：Web服务、任务调度、数据存储
- 云端(AutoDL)：纯模型推理服务

---

## 快速部署

```bash
# 1. AutoDL启动vLLM
python -m vllm.entrypoints.openai.api_server \
    --model Qwen/Qwen3-VL-8B-Instruct \
    --host 0.0.0.0 --port 8000

# 2. 本地配置.env
MODEL_SERVICE_TYPE=vllm
VLLM_HOST=http://autodl-xxx:8000

# 3. 启动本地服务
celery -A celery_app worker --concurrency=1
python app.py
```

详见 [DEPLOYMENT.md](./DEPLOYMENT.md)

---

## 剩余阶段

### 阶段4：移动端适配（可选）

- [ ] 响应式设计
- [ ] PWA支持
- [ ] 图片压缩

---

**文档更新时间**: 2026-05-02