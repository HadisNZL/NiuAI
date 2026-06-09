#!/bin/bash
cd "$(dirname "$0")"
echo "🚀 启动 NIU AI..."
python3 app.py &
sleep 2
echo "✅ 访问 http://localhost:8088"
