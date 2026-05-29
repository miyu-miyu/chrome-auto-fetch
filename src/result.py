"""
结果保存 — JSON, 历史记录, 文本报告
"""

import json
import os
import logging

log = logging.getLogger("chrome_auto_fetch")


def save_result(result_data, config):
    """保存结果到 JSON 文件、历史记录和文本报告"""
    os.makedirs(config["OUTPUT_DIR"], exist_ok=True)

    result_file = os.path.join(config["OUTPUT_DIR"], "latest_result.json")
    with open(result_file, "w", encoding="utf-8") as f:
        json.dump(result_data, f, ensure_ascii=False, indent=2)
    log.info("结果已保存: %s", result_file)

    history_file = os.path.join(config["OUTPUT_DIR"], "history.json")
    history = []
    if os.path.exists(history_file):
        try:
            with open(history_file, "r", encoding="utf-8") as f:
                history = json.load(f)
        except json.JSONDecodeError:
            history = []
    history.append(result_data)
    with open(history_file, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

    report_file = os.path.join(config["OUTPUT_DIR"], "latest_report.txt")
    with open(report_file, "w", encoding="utf-8") as f:
        f.write("时间: %s\n" % result_data['timestamp'])
        f.write("状态: %s\n" % result_data['status'])
        if result_data.get("error"):
            f.write("错误: %s\n" % result_data['error'])
        if result_data.get("download_urls"):
            f.write("\n下载地址:\n")
            for url in result_data["download_urls"]:
                f.write("  %s\n" % url)
        else:
            f.write("\n未找到下载地址\n")