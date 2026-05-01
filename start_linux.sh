#!/bin/bash

# 车辆识别系统 Linux 启动脚本
# 支持多种运行模式：mock / ollama / vllm

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=========================================="
echo "  车辆识别系统 - Linux启动脚本"
echo "=========================================="

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 检查虚拟环境
if [ ! -d ".venv" ]; then
    echo -e "${YELLOW}创建虚拟环境...${NC}"
    python3 -m venv .venv
fi

# 激活虚拟环境
echo -e "${GREEN}激活虚拟环境...${NC}"
source .venv/bin/activate

# 检查依赖
if ! python -c "import flask" 2>/dev/null; then
    echo -e "${YELLOW}安装依赖...${NC}"
    pip install -r backend/requirements.txt
fi

# 设置默认配置
export INFERENCE_BACKEND="${INFERENCE_BACKEND:-mock}"
export MOCK_DELAY="${MOCK_DELAY:-2.0}"
export CELERY_BROKER_TYPE="${CELERY_BROKER_TYPE:-sqlalchemy}"
export JWT_SECRET_KEY="${JWT_SECRET_KEY:-your-secret-key-change-in-production}"

# 显示配置
echo ""
echo "当前配置："
echo "  推理后端: $INFERENCE_BACKEND"
echo "  Celery Broker: $CELERY_BROKER_TYPE"
echo ""

# 根据后端类型检查依赖
case $INFERENCE_BACKEND in
    ollama)
        if ! command -v ollama &> /dev/null; then
            echo -e "${RED}错误：Ollama未安装${NC}"
            echo "请运行：curl -fsSL https://ollama.com/install.sh | sh"
            exit 1
        fi
        echo -e "${GREEN}检查Ollama服务...${NC}"
        if ! ollama list &> /dev/null; then
            echo -e "${YELLOW}启动Ollama服务...${NC}"
            ollama serve &
            sleep 3
        fi
        # 检查模型
        MODEL_NAME="${OLLAMA_MODEL:-qwen3-vl:8b}"
        if ! ollama list | grep -q "$MODEL_NAME"; then
            echo -e "${YELLOW}下载模型 $MODEL_NAME...${NC}"
            ollama pull "$MODEL_NAME"
        fi
        ;;
    vllm)
        if [ -z "$VLLM_API_URL" ]; then
            echo -e "${RED}错误：使用vLLM后端需要设置 VLLM_API_URL 环境变量${NC}"
            exit 1
        fi
        echo -e "${GREEN}vLLM后端配置：$VLLM_API_URL${NC}"
        ;;
    mock)
        echo -e "${GREEN}使用Mock后端（测试模式）${NC}"
        ;;
    *)
        echo -e "${RED}错误：未知的推理后端 $INFERENCE_BACKEND${NC}"
        exit 1
        ;;
esac

# 创建上传目录
mkdir -p uploads

# 获取WSL IP地址（用于Windows浏览器访问）
WSL_IP=$(hostname -I | awk '{print $1}')
echo ""
echo -e "${GREEN}服务访问地址：${NC}"
echo "  Linux本地: http://127.0.0.1:5000"
echo "  Windows浏览器: http://$WSL_IP:5000"
echo ""

# 启动Celery Worker（后台）
echo -e "${GREEN}启动Celery Worker...${NC}"
cd backend
celery -A celery_app worker --loglevel=info --concurrency=2 &
CELERY_PID=$!
cd ..

# 等待Celery启动
sleep 2

# 启动Flask应用
echo -e "${GREEN}启动Flask应用...${NC}"
echo -e "${YELLOW}按 Ctrl+C 停止服务${NC}"
echo ""

# 捕获Ctrl+C信号
cleanup() {
    echo ""
    echo -e "${YELLOW}停止服务...${NC}"
    kill $CELERY_PID 2>/dev/null || true
    exit 0
}
trap cleanup INT TERM

cd backend
python app.py

# 清理
cleanup