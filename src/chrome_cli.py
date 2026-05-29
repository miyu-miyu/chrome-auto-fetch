"""
Chrome DevTools CLI 封装
========================

提供所有 chrome-devtools 命令的 Python 接口。
通过 connection.py 自动发现连接地址。
"""

import subprocess
import json
import re
import logging

from .connection import resolve_connection

log = logging.getLogger("chrome_auto_fetch")


class ChromeDevTools:

    DEBUG_PORT = 9333

    def __init__(self, config):
        self.cli = config["CLI_PATH"]
        self.target = None
        self._base_args = resolve_connection(config)
        if config.get("CHANNEL", "stable") != "stable":
            self._base_args += ["--channel", config["CHANNEL"]]

    def _cmd(self, subcmd, extra_args=None):
        args = [self.cli] + self._base_args
        if self.target:
            args += ["--target", self.target]
        args.append(subcmd)
        if extra_args:
            args += extra_args
        return args

    def _run(self, args, timeout=30, json_output=False):
        if json_output:
            args += ["--json"]
        log.debug("CMD: %s", " ".join(args))
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        log.debug("EXIT: %d | STDOUT: %s | STDERR: %s",
                  result.returncode, result.stdout[:200], result.stderr[:200])
        if result.returncode != 0:
            raise RuntimeError(
                "命令失败 (exit=%d): %s" % (result.returncode, result.stderr or result.stdout)
            )
        return result

    def navigate(self, url):
        result = self._run(self._cmd("navigate", [url]), timeout=60)
        output = result.stdout.strip()
        match = re.search(r'\[target:(\w+-\w+)\]', output)
        if match:
            self.target = match.group(1)
            log.info("导航成功: %s → target=%s", url, self.target)
        else:
            log.warning("未捕获 target name, 使用默认 page 0")
        return output

    def snapshot_json(self):
        result = self._run(self._cmd("snapshot"), json_output=True, timeout=30)
        return json.loads(result.stdout)

    def snapshot_text(self):
        result = self._run(self._cmd("snapshot"), timeout=30)
        return result.stdout

    def fill(self, selector, value):
        result = self._run(self._cmd("fill", [selector, value]), timeout=15)
        log.info("填入: %s → %s", selector, value)
        return result.stdout.strip()

    def click(self, selector):
        result = self._run(self._cmd("click", [selector]), timeout=15)
        log.info("点击: %s", selector)
        return result.stdout.strip()

    def click_at(self, x, y):
        result = self._run(self._cmd("click-at", [str(x), str(y)]), timeout=15)
        log.info("点击坐标: (%s, %s)", x, y)
        return result.stdout.strip()

    def type_text(self, text, submit_key=None):
        extra = [text]
        if submit_key:
            extra += ["--submit-key", submit_key]
        result = self._run(self._cmd("type-text", extra), timeout=15)
        log.info("输入文本: %s%s", text, " +" + submit_key if submit_key else "")
        return result.stdout.strip()

    def press_key(self, key):
        result = self._run(self._cmd("press-key", [key]), timeout=10)
        log.info("按键: %s", key)
        return result.stdout.strip()

    def wait_for(self, text, timeout_ms=30000):
        result = self._run(
            self._cmd("wait-for", [text, "--timeout", str(timeout_ms)]),
            timeout=timeout_ms // 1000 + 10,
        )
        log.info("等待文本出现: %s", text)
        return result.stdout.strip()

    def evaluate(self, expr):
        result = self._run(self._cmd("evaluate", [expr]), timeout=15)
        log.info("执行JS: %s", expr[:80])
        return result.stdout.strip()

    def evaluate_json(self, expr):
        result = self._run(self._cmd("evaluate", [expr]), json_output=True, timeout=15)
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            return {"raw": result.stdout.strip()}

    def screenshot(self, output_path):
        result = self._run(
            self._cmd("screenshot", ["--output", output_path]),
            timeout=15,
        )
        log.info("截图保存: %s", output_path)
        return result.stdout.strip()

    def list_pages(self):
        result = self._run(self._cmd("list-pages"), timeout=10)
        return result.stdout.strip()

    def new_page(self, url):
        result = self._run(self._cmd("new-page", [url]), timeout=30)
        match = re.search(r'\[target:(\w+-\w+)\]', result.stdout)
        if match:
            self.target = match.group(1)
        return result.stdout.strip()