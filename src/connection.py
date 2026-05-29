"""
Chrome 连接发现模块
====================

负责发现 Chrome DevTools Protocol 的 WebSocket 连接地址。

连接策略优先级:
  1. WS_ENDPOINT — 用户显式指定的 WebSocket URL (最高优先级)
  2. DevToolsActivePort — 从 Chrome profile 目录读取调试端口文件
  3. HTTP 发现 — 通过 /json/version HTTP 端点自动发现 WebSocket URL
"""

import os
import json
import subprocess
import logging

log = logging.getLogger("chrome_auto_fetch")

DEFAULT_DEBUG_PORT = 9333


def discover_ws_url(port):
    """通过 /json/version HTTP 端点发现 WebSocket URL

    Args:
        port: Chrome 远程调试端口 (默认 9333)

    Returns:
        WebSocket URL 字符串, 发现失败返回空字符串
    """
    try:
        result = subprocess.run(
            ["curl", "-s", "http://127.0.0.1:%d/json/version" % port],
            capture_output=True, text=True, timeout=5,
        )
        data = json.loads(result.stdout)
        ws_url = data.get("webSocketDebuggerUrl", "")
        if ws_url:
            log.info("自动发现 WebSocket URL: %s", ws_url)
            return ws_url
    except Exception:
        pass
    return ""


def read_devtools_active_port(user_data_dir):
    """读取 Chrome DevToolsActivePort 文件

    Args:
        user_data_dir: Chrome 用户数据目录路径 (支持 ~ 展开)

    Returns:
        (port, ws_path) 元组, 读取失败返回 None
    """
    expanded_dir = os.path.expanduser(user_data_dir)
    port_file = os.path.join(expanded_dir, "DevToolsActivePort")
    if not os.path.exists(port_file):
        return None
    try:
        with open(port_file, "r") as f:
            lines = f.read().strip().split("\n")
        if len(lines) >= 2:
            port = int(lines[0].strip())
            ws_path = lines[1].strip()
            log.info("从 DevToolsActivePort 读取: port=%d, path=%s", port, ws_path)
            return (port, ws_path)
    except Exception as e:
        log.warning("读取 DevToolsActivePort 失败: %s", e)
    return None


def resolve_connection(config):
    """根据配置决定连接策略, 返回 CLI 基础参数列表

    连接优先级:
      1. WS_ENDPOINT — 直接使用指定的 WebSocket URL
      2. USER_DATA_DIR + DevToolsActivePort — 从 profile 目录发现
      3. HTTP 发现 — 通过 /json/version 自动发现

    Args:
        config: 配置字典, 需包含 WS_ENDPOINT, USER_DATA_DIR, CHANNEL 等字段

    Returns:
        CLI 基础参数列表 (如 ["--ws-endpoint", "ws://..."] 或 ["--user-data-dir", "/path"])
    """
    base_args = []

    # 优先级 1: 显式指定的 WebSocket URL
    ws_endpoint = config.get("WS_ENDPOINT", "")
    if ws_endpoint:
        base_args += ["--ws-endpoint", ws_endpoint]
        return base_args

    # 优先级 2: 从 DevToolsActivePort 发现
    user_data_dir = config.get("USER_DATA_DIR", "")
    if user_data_dir:
        expanded_dir = os.path.expanduser(user_data_dir)
        port_file = os.path.join(expanded_dir, "DevToolsActivePort")
        if os.path.exists(port_file):
            base_args += ["--user-data-dir", expanded_dir]
            return base_args

    # 优先级 3: HTTP 发现
    port = config.get("DEBUG_PORT", DEFAULT_DEBUG_PORT)
    ws_url = discover_ws_url(port)
    if ws_url:
        base_args += ["--ws-endpoint", ws_url]
        return base_args

    log.warning("既无 DevToolsActivePort 也无法发现 WebSocket URL, 将使用 CLI 默认连接方式")
    return base_args