#!/bin/bash

# 进入项目目录
cd /www/wwwroot/gupiao-tv

# 激活虚拟环境
source venv/bin/activate

# 设置环境变量
export FLASK_APP=app.py
export FLASK_ENV=production

# 确保日志目录存在
mkdir -p logs

# 使用 Gunicorn 启动应用
gunicorn wsgi:app \
    --bind 0.0.0.0:5000 \
    --workers 4 \
    --threads 2 \
    --worker-class gthread \
    --access-logfile logs/access.log \
    --error-logfile logs/error.log \
    --capture-output \
    --daemon 