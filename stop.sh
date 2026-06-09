#!/bin/bash
PORT=8088
PIDS=$(lsof -ti :$PORT 2>/dev/null)
if [ -z "$PIDS" ]; then
    echo "🟢 端口 $PORT 没有被占用，服务已停止"
else
    kill -9 $PIDS 2>/dev/null
    echo "🛑 已停止端口 $PORT 上的服务 (PID: $PIDS)"
fi
