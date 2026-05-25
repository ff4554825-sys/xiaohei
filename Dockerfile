FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    git curl \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 安装项目
COPY . .
RUN pip install -e .

# 默认端口
EXPOSE 3721

# 入口
CMD ["python", "start.py", "--mode", "web", "--host", "0.0.0.0"]
