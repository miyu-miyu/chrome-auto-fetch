#!/bin/bash
# macOS Chrome 远程调试启动脚本
# 使用 open -na 强制启动新 Chrome 实例 (与日常 Chrome 并存)
# 日常 Chrome 占用端口 9222, debug Chrome 使用端口 9333

PROFILE_DIR="$HOME/chrome-debug-profile"
PORT=9333

# 幂等检查: 如果 debug Chrome 已在运行, 跳过启动
if curl -s "http://127.0.0.1:$PORT/json/version" > /dev/null 2>&1; then
    echo "Debug Chrome 已在运行 (端口 $PORT)"
    echo "WebSocket 信息:"
    curl -s "http://127.0.0.1:$PORT/json/version" | python3 -m json.tool 2>/dev/null || \
        curl -s "http://127.0.0.1:$PORT/json/version"
    echo ""
    echo "当前页面:"
    curl -s "http://127.0.0.1:$PORT/json/list" | python3 -c "
import sys, json
try:
    pages = json.load(sys.stdin)
    for p in pages:
        print('  [%s] %s — %s' % (p.get('id','?'), p.get('title','?'), p.get('url','?')))
except: pass
" 2>/dev/null || curl -s "http://127.0.0.1:$PORT/json/list"
    exit 0
fi

# 创建 profile 目录 (如果不存在)
mkdir -p "$PROFILE_DIR"

# 启动 Chrome (open -na 强制新实例)
open -na "Google Chrome" --args \
    --remote-debugging-port=$PORT \
    --user-data-dir="$PROFILE_DIR" \
    --no-first-run \
    --disable-background-networking \
    --disable-default-apps \
    --disable-extensions

# 等待 Chrome 启动并验证连接
echo "等待 Chrome 启动..."
for i in $(seq 1 10); do
    sleep 1
    if curl -s "http://127.0.0.1:$PORT/json/version" > /dev/null 2>&1; then
        echo "Chrome 已启动, 远程调试端口: $PORT"
        echo "WebSocket 信息:"
        curl -s "http://127.0.0.1:$PORT/json/version" | python3 -m json.tool 2>/dev/null || \
            curl -s "http://127.0.0.1:$PORT/json/version"
        exit 0
    fi
done

echo "警告: Chrome 启动超时, 请检查 Chrome 是否正常运行"
exit 1