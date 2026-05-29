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
        self._ensure_page()

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

    def _ensure_page(self):
        try:
            result = self._run(self._cmd("list-pages"), timeout=5)
            pages = result.stdout.strip()
            if not pages or "No pages" in pages:
                log.info("Chrome 无打开页面, 自动创建空白页")
                self._run(self._cmd("new-page", ["about:blank"]), timeout=10)
        except RuntimeError:
            log.info("Chrome 连接异常或无页面, 尝试创建空白页")
            try:
                self._run(self._cmd("new-page", ["about:blank"]), timeout=10)
            except RuntimeError:
                log.warning("无法创建空白页, Chrome 可能未启动")

    def _capture_target(self, source=None):
        """从 list-pages --json 获取 page 0 的 target name, 或从命令输出提取 target。

        navigate 命令不输出 target 信息, 需要通过 list-pages 获取。
        new-page 命令输出 '(target: HEXID)', 需要用正则提取。
        """
        if source:
            # 匹配 '(target: HEXID)' 或 '[target: name-name]'
            match = re.search(r'\(target:\s*(\w+)\)|\[target:\s*([A-Za-z0-9_-]+)\]', source)
            if match:
                self.target = match.group(1) or match.group(2)
                log.debug("从命令输出捕获 target: %s", self.target)
                return True

        # fallback: 通过 list-pages --json 获取 page 0 的 target
        try:
            result = self._run(self._cmd("list-pages") + ["--json"], timeout=10)
            pages = json.loads(result.stdout)
            if pages and len(pages) > 0:
                page0 = pages[0]
                self.target = page0.get("target", "")
                log.debug("从 list-pages 捕获 target: %s", self.target)
                return True
        except (json.JSONDecodeError, RuntimeError) as e:
            log.debug("list-pages JSON 解析失败: %s", e)
        return False

    def navigate(self, url):
        result = self._run(self._cmd("navigate", [url]), timeout=60)
        output = result.stdout.strip()
        if self._capture_target(source=output):
            log.info("导航成功: %s → target=%s", url, self.target)
        else:
            if self.target:
                log.info("导航成功: %s → target=%s (via list-pages)", url, self.target)
            else:
                log.warning("导航完成但无法获取 target, 使用默认 page 0")
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
        self._capture_target(source=result.stdout)
        return result.stdout.strip()