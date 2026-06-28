#!/bin/bash
echo "========================================="
echo "  TechMall 一键启动脚本"
echo "========================================="

cd "$(dirname "$0")"

# 检查数据库是否存在，不存在则初始化
if [ ! -f "db.sqlite3" ]; then
    echo "[1/3] 初始化数据库..."
    python manage.py migrate
    python manage.py loaddata Shop/fixtures/initial_data.json
    echo "  -> 数据库初始化完成"
else
    echo "[1/3] 数据库已存在，跳过初始化"
fi

echo "[2/3] 检查依赖..."
pip install -r requirements.txt -q 2>/dev/null

echo "[3/3] 启动服务器..."
echo ""
echo "  访问地址: http://127.0.0.1:8000/"
echo "  后台管理: http://127.0.0.1:8000/admin/"
echo "  按 Ctrl+C 停止服务"
echo "========================================="
echo ""
python manage.py runserver
