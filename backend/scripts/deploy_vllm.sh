#!/bin/bash
# vLLM云端部署脚本（AutoDL）
# 在云端GPU服务器上运行此脚本启动vLLM推理服务

set -e

# 配置
MODEL_NAME="${VLLM_MODEL:-qwen3-vl:8b}"
PORT="${VLLM_PORT:-8000}"
API_KEY="${VLLM_API_KEY:-}"

echo "=========================================="
echo "vLLM推理服务部署脚本"
echo "模型: $MODEL_NAME"
echo "端口: $PORT"
echo "=========================================="

# 检查GPU
echo "检查GPU状态..."
nvidia-smi

# 检查conda环境
if ! command -v conda &> /dev/null; then
    echo "安装Miniconda..."
    wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O miniconda.sh
    bash miniconda.sh -b -p $HOME/miniconda
    export PATH="$HOME/miniconda/bin:$PATH"
fi

# 创建conda环境
ENV_NAME="vllm_env"
if ! conda env list | grep -q "$ENV_NAME"; then
    echo "创建conda环境: $ENV_NAME"
    conda create -n $ENV_NAME python=3.10 -y
fi

# 激活环境
source $(conda info --base)/etc/profile.d/conda.sh
conda activate $ENV_NAME

# 安装依赖
echo "安装vLLM..."
pip install vllm==0.4.2 transformers==4.40.0 torch==2.2.0

# 下载模型（如果不存在）
echo "准备模型: $MODEL_NAME"
MODEL_DIR="$HOME/.cache/vllm/$MODEL_NAME"
if [ ! -d "$MODEL_DIR" ]; then
    echo "下载模型..."
    # 这里假设模型已下载，或使用huggingface缓存
    # 实际部署时需要根据具体模型调整
fi

# 启动vLLM服务
echo "启动vLLM服务..."
if [ -z "$API_KEY" ]; then
    # 无需API密钥
    python -m vllm.entrypoints.openai.api_server \
        --model "$MODEL_NAME" \
        --port $PORT \
        --host 0.0.0.0 \
        --trust-remote-code \
        --max-model-len 4096 \
        --tensor-parallel-size 1 \
        --gpu-memory-utilization 0.9
else
    # 需要API密钥
    python -m vllm.entrypoints.openai.api_server \
        --model "$MODEL_NAME" \
        --port $PORT \
        --host 0.0.0.0 \
        --trust-remote-code \
        --max-model-len 4096 \
        --tensor-parallel-size 1 \
        --gpu-memory-utilization 0.9 \
        --api-key "$API_KEY"
fi

echo "vLLM服务已启动在端口 $PORT"