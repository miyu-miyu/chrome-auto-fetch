#!/usr/bin/env python3
"""
chrome-auto-fetch CLI 入口
==========================

使用方式:
  1. 先运行 discovery 模式, 获取页面结构, 填入配置中的 CSS 选择器
  2. 再运行 auto 模式, 执行完整的自动化流程
  3. 用 cron 或 daemon 模式实现每日定时执行
"""

import os
import sys
import logging
import argparse
from pathlib import Path

from src.chrome_cli import ChromeDevTools
from src.discover import discover
from src.step_engine import run_steps, run_steps_with_retry
from src.scheduler import setup_cron, setup_schedule_daemon

log = logging.getLogger("chrome_auto_fetch")

DEFAULT_CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config", "config.yaml")

DEFAULTS = {
    "CLI_PATH": "",
    "TARGET_URL": "",
    "STEPS": [],
    "WS_ENDPOINT": "",
    "USER_DATA_DIR": "~/chrome-debug-profile",
    "CHANNEL": "stable",
    "OUTPUT_DIR": str(Path.home() / "chrome-devtools-downloads"),
    "LOG_FILE": str(Path.home() / "chrome-devtools-downloads" / "auto_download.log"),
    "MAX_RETRIES": 3,
    "STEP_DELAY": 2,
    "MAX_STEPS": 100,
    "MAX_EXECUTIONS": 500,
    "SCHEDULE_TIME": "09:00",
}


def load_config(config_path):
    """从 YAML 文件加载配置, 合并默认值"""
    config = dict(DEFAULTS)

    if os.path.exists(config_path):
        try:
            import yaml
            with open(config_path, "r", encoding="utf-8") as f:
                yaml_config = yaml.safe_load(f)
            if yaml_config and isinstance(yaml_config, dict):
                config.update(yaml_config)
        except ImportError:
            print("警告: PyYAML 未安装, 使用默认配置")
            print("安装方法: pip install pyyaml")
        except Exception as e:
            print("警告: 配置文件读取失败 (%s), 使用默认配置" % e)

    # 平台特定的 CLI_PATH 默认值
    if not config["CLI_PATH"]:
        if sys.platform == "darwin":
            config["CLI_PATH"] = "/usr/local/bin/chrome-devtools"
        elif sys.platform.startswith("linux"):
            config["CLI_PATH"] = "/usr/local/bin/chrome-devtools"
        elif sys.platform == "win32":
            config["CLI_PATH"] = "chrome-devtools.exe"

    # 展开 ~ 为 home 目录 (YAML 加载不自动展开)
    for key in ("OUTPUT_DIR", "LOG_FILE", "USER_DATA_DIR"):
        if config.get(key):
            config[key] = os.path.expanduser(config[key])

    return config


def setup_logging(config):
    """配置日志输出"""
    os.makedirs(config["OUTPUT_DIR"], exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(config["LOG_FILE"], encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )


def main():
    parser = argparse.ArgumentParser(
        description="chrome-auto-fetch 自动化下载框架",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用模式:
  --mode discover   探索页面结构, 确定 CSS 选择器 (首次使用必跑)
  --mode auto       执行自动化下载流程
  --mode cron       生成 crontab 定时任务配置
  --mode daemon     Python 内置调度器模式 (长期运行)

首次使用流程:
  1. 填写 config/config.yaml 中的 TARGET_URL 和 CLI_PATH
  2. python3 main.py --mode discover
  3. 根据输出编写 STEPS 步骤配置
  4. python3 main.py --mode auto
  5. (可选) python3 main.py --mode cron 设置定时
        """,
    )
    parser.add_argument(
        "--mode",
        choices=["discover", "auto", "cron", "daemon"],
        default="auto",
        help="运行模式",
    )
    parser.add_argument(
        "--config",
        default=DEFAULT_CONFIG_PATH,
        help="配置文件路径 (默认: config/config.yaml)",
    )
    args = parser.parse_args()

    config = load_config(args.config)
    setup_logging(config)

    cli = ChromeDevTools(config)

    if args.mode == "discover":
        discover(cli, config)
    elif args.mode == "auto":
        result = run_steps_with_retry(cli, config)
        print("\n结果: %s" % result['status'])
        if result.get("download_urls"):
            print("下载地址:")
            for url in result["download_urls"]:
                print("  → %s" % url)
        elif result.get("error"):
            print("错误: %s" % result['error'])
    elif args.mode == "cron":
        setup_cron(config)
    elif args.mode == "daemon":
        setup_schedule_daemon(config)


if __name__ == "__main__":
    main()