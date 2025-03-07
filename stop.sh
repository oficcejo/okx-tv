#!/bin/bash

# 查找并终止 Gunicorn 主进程
pkill -f "gunicorn wsgi:app"

# 等待进程完全终止
sleep 2

# 检查是否还有残留进程
if pgrep -f "gunicorn wsgi:app" > /dev/null; then
    echo "强制终止残留进程..."
    pkill -9 -f "gunicorn wsgi:app"
fi

echo "服务已停止" 