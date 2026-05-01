# ==========================================
# 车辆识别系统 - Docker镜像
# ==========================================

FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目文件
COPY . .

# 创建上传目录
RUN mkdir -p uploads

# 暴露端口
EXPOSE 5000

# 环境变量
ENV PYTHONUNBUFFERED=1
ENV ENV=production
ENV DEBUG=False

# 启动命令（通过docker-compose覆盖）
CMD ["python", "app.py"]