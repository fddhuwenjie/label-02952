# 拼音输入法引擎 Dockerfile
# 支持 ARM64 和 AMD64 架构

# 使用官方 Python 镜像（支持多架构）
FROM --platform=$BUILDPLATFORM python:3.11-slim AS builder

# 设置工作目录
WORKDIR /app

# 复制依赖文件
COPY requirements.txt .

# 安装依赖（如果有的话）
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY app/ ./app/

# 编译 Python 字节码以提升启动速度
RUN python -m compileall -b app/

# 生产镜像
FROM python:3.11-slim

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8

# 创建非 root 用户
RUN groupadd --gid 1000 appgroup && \
    useradd --uid 1000 --gid appgroup --shell /bin/bash --create-home appuser

WORKDIR /app

# 从构建阶段复制编译后的代码
COPY --from=builder /app/app ./app/

# 复制并安装依赖（如果有的话）
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages

# 设置文件权限
RUN chown -R appuser:appgroup /app

# 切换到非 root 用户
USER appuser

# 默认命令：交互模式
CMD ["python", "-m", "app"]
