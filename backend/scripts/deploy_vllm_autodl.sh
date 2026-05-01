#!/bin/bash
# ==========================================
# vLLM 云端部署脚本 - AutoDL
# ==========================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}==========================================${NC}"
echo -e "${GREEN}   vLLM AutoDL 部署脚本${NC}"
echo -e "${GREEN}==========================================${NC}"

# 默认配置
MODEL_NAME=${MODEL_NAME:-"qwen3-vl:8b"}
PORT=${PORT:-8000}
GPU_MEMORY_UTILIZATION=${GPU_MEMORY_UTILIZATION:-0.85}
MAX_MODEL_LEN=${MAX_MODEL_LEN:-8192}
TENSOR_PARALLEL_SIZE=${TENSOR_PARALLEL_SIZE:-1}

echo -e "${YELLOW}配置信息:${NC}"
echo "  模型: $MODEL_NAME"
echo "  端口: $PORT"
echo "  GPU利用率: $GPU_MEMORY_UTILIZATION"
echo "  最大上下文: $MAX_MODEL_LEN"
echo "  张量并行: $TENSOR_PARALLEL_SIZE"

# 检查是否安装了vLLM
echo -e "\n${YELLOW}[1/5] 检查vLLM安装...${NC}"
if ! python -c "import vllm" 2>/dev/null; then
    echo -e "${YELLOW}vLLM未安装，正在安装...${NC}"
    pip install vllm==0.5.0 -i https://pypi.tuna.tsinghua.edu.cn/simple
    echo -e "${GREEN}vLLM安装完成${NC}"
else
    echo -e "${GREEN}vLLM已安装${NC}"
fi

# 检查模型是否存在
echo -e "\n${YELLOW}[2/5] 检查模型...${NC}"
if [ ! -d "~/.cache/modelscope/hub/$MODEL_NAME" ] && [ ! -d "/root/autodl-tmp/$MODEL_NAME" ]; then
    echo -e "${YELLOW}模型未找到，需要下载${NC}"
    echo -e "${YELLOW}请先将模型下载到 /root/autodl-tmp/ 目录${NC}"
    echo "下载命令示例:"
    echo "  modelscope download --model qwen/$MODEL_NAME --local_dir /root/autodl-tmp/$MODEL_NAME"
fi

# 查找模型路径
MODEL_PATH=""
if [ -d "/root/autodl-tmp/$MODEL_NAME" ]; then
    MODEL_PATH="/root/autodl-tmp/$MODEL_NAME"
elif [ -d "~/.cache/modelscope/hub/$MODEL_NAME" ]; then
    MODEL_PATH="~/.cache/modelscope/hub/$MODEL_NAME"
else
    # 使用模型名称直接加载（会从HuggingFace下载）
    MODEL_PATH=$MODEL_NAME
fi

echo "模型路径: $MODEL_PATH"

# 检查端口占用
echo -e "\n${YELLOW}[3/5] 检查端口 $PORT...${NC}"
if lsof -i:$PORT >/dev/null 2>&1; then
    echo -e "${RED}端口 $PORT 已被占用${NC}"
    echo "尝试释放端口..."
    lsof -ti:$PORT | xargs kill -9 2>/dev/null || true
    sleep 2
fi
echo -e "${GREEN}端口 $PORT 可用${NC}"

# 启动vLLM服务
echo -e "\n${YELLOW}[4/5] 启动vLLM服务...${NC}"
echo -e "${YELLOW}启动命令:${NC}"

# 构建启动命令
START_CMD="python -m vllm.entrypoints.openai.api_server \
    --model $MODEL_PATH \
    --host 0.0.0.0 \
    --port $PORT \
    --gpu-memory-utilization $GPU_MEMORY_UTILIZATION \
    --max-model-len $MAX_MODEL_LEN \
    --tensor-parallel-size $TENSOR_PARALLEL_SIZE"

# 可选配置
if [ "$ENABLE_PREFIX_CACHING" = "true" ]; then
    START_CMD="$START_CMD --enable-prefix-caching"
fi

if [ "$API_KEY" ]; then
    START_CMD="$START_CMD --api-key $API_KEY"
fi

echo "$START_CMD"

# 后台启动
nohup $START_CMD > vllm_server.log 2>&1 &

# 等待服务启动
echo -e "\n${YELLOW}[5/5] 等待服务启动...${NC}"
sleep 5

# 健康检查
for i in {1..30}; do
    if curl -s http://localhost:$PORT/health >/dev/null 2>&1; then
        echo -e "${GREEN}✓ vLLM服务启动成功！${NC}"
        echo -e "\n${GREEN}==========================================${NC}"
        echo -e "${GREEN}服务信息:${NC}"
        echo "  API地址: http://$(hostname -I | awk '{print $1}'):$PORT"
        echo "  健康检查: http://localhost:$PORT/health"
        echo "  模型列表: http://localhost:$PORT/v1/models"
        echo "  日志文件: vllm_server.log"
        echo -e "${GREEN}==========================================${NC}"
        
        # 显示公网访问地址
        echo -e "\n${YELLOW}公网访问配置:${NC}"
        echo "在本地.env文件中设置:"
        echo "  MODEL_SERVICE_TYPE=vllm"
        echo "  VLLM_HOST=http://$(curl -s ifconfig.me):$PORT"
        echo ""
        echo "注意: 需要在AutoDL控制台开放 $PORT 端口"
        
        exit 0
    fi
    echo "等待服务启动... ($i/30)"
    sleep 2
done

echo -e "${RED}✗ 服务启动失败，请检查日志:${NC}"
echo "  tail -f vllm_server.log"
exit 1