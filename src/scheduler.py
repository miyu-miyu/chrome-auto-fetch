"""
定时调度 — crontab 和 Python schedule daemon
"""

import os
import sys
import time
import logging

log = logging.getLogger("chrome_auto_fetch")


def setup_cron(config):
    """生成 crontab 定时任务配置行"""
    script_path = os.path.abspath(sys.argv[0])
    project_dir = os.path.dirname(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "main.py")))
    cron_time = config["SCHEDULE_TIME"]
    hour, minute = cron_time.split(":")
    cron_expr = "%s %s * * *" % (minute, hour)

    cron_line = "%s cd %s && python3 main.py --mode auto >> %s 2>&1" % (
        cron_expr, project_dir, config['LOG_FILE']
    )

    print("\n" + "=" * 60)
    print("  Schedule 模式 — 设置定时任务")
    print("=" * 60 + "\n")
    print("执行时间: 每天 %s" % cron_time)
    print("执行命令: %s\n" % cron_line)

    print("请将以下行添加到 crontab:")
    print("-" * 40)
    print(cron_line)
    print("-" * 40)
    print()

    print("添加方法:")
    print("  1. 运行: crontab -e")
    print("  2. 将上面的行粘贴到文件末尾")
    print("  3. 保存退出")
    print()

    print("验证:")
    print("  crontab -l  # 查看已添加的定时任务")
    print()

    if sys.platform == "darwin":
        print("macOS 注意:")
        print("  如果 cron 无法执行, 需要:")
        print("  1. 系统设置 → 隐私与安全性 → 辅助功能")
        print("  2. 添加 /usr/sbin/cron 到允许列表")
        print()


def setup_schedule_daemon(config):
    """使用 Python schedule 库实现定时调度守护进程"""
    try:
        import schedule
    except ImportError:
        print("需要安装 schedule 库:")
        print("  pip3 install schedule")
        print()
        print("或者使用 cron 方式:")
        print("  python3 main.py --mode cron")
        return

    from .chrome_cli import ChromeDevTools
    from .step_engine import run_steps_with_retry

    cli = ChromeDevTools(config)
    hour, minute = config["SCHEDULE_TIME"].split(":")
    time_str = "%s:%s" % (hour, minute)

    print("\n" + "=" * 60)
    print("  Schedule Daemon — 每天定时 %s 执行" % time_str)
    print("=" * 60 + "\n")

    def job():
        log.info("--- 定时任务开始 ---")
        result = run_steps_with_retry(cli, config)
        log.info("--- 定时任务结束: %s ---", result["status"])

    schedule.every().day.at(time_str).do(job)

    print("调度器已启动, 每天 %s 自动执行..." % time_str)
    print("按 Ctrl+C 停止\n")

    while True:
        schedule.run_pending()
        time.sleep(60)