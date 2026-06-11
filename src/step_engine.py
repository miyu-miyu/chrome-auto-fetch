"""
步骤引擎 — 解析 STEPS 配置, 按序执行可编排的动作序列

支持 17 种 action: navigate, fill, click, click_at, hover, type_text, press_key,
wait (5 种策略), evaluate, extract, loop, screenshot, snapshot, new_page,
list_pages, save, branch

所有 click 操作使用 CDP 鼠标事件 (dispatchMouseEvent), 不再使用 JS .click():
  - selector 模式: scrollIntoView → cli.click() (CDP)
  - match:text 模式: JS 查找元素 → scrollIntoView → cli.click_at() (CDP)
  - index!=1 模式: JS 查找元素 → scrollIntoView → cli.click_at() (CDP)

自动规避遮挡: scrollIntoView({block:'center'}) + elementFromPoint 检测 + 偏移重试

步骤可选 name 字段: 用于日志显示和 branch goto 按名称跳转
branch 条件关键字: branches 列表格式 [{if, then}, {elif, then}, {else: 目标}]

安全限制: MAX_STEPS (硬上限 200) 验证配置步数, MAX_EXECUTIONS (硬上限 1000) 防止无限循环

STEPS 为必填配置 — 不配 STEPS 时程序报错终止
"""

import json
import os
import re
import time
import logging
from datetime import datetime

from .result import save_result

log = logging.getLogger("chrome_auto_fetch")

_SCROLL_VIEW_JS = r"""
(() => {
  const sel = %s;
  const idx = %s;
  const el = (idx === null)
    ? document.querySelector(sel)
    : document.querySelectorAll(sel)[idx];
  if (!el) return JSON.stringify({error: 'element not found'});
  el.scrollIntoView({block: 'center', behavior: 'instant'});
  const rect = el.getBoundingClientRect();
  const cx = Math.round(rect.x + rect.width / 2);
  const cy = Math.round(rect.y + rect.height / 2);
  const hitEl = document.elementFromPoint(cx, cy);
  const isTarget = (hitEl === el || el.contains(hitEl));
  let occluderHeight = 0;
  let offsetY = 0;
  if (!isTarget && hitEl) {
    occluderHeight = Math.round(hitEl.getBoundingClientRect().height);
    offsetY = cy - occluderHeight - 10;
    const hitAfter = document.elementFromPoint(cx, offsetY);
    const isTargetAfter = (hitAfter === el || el.contains(hitAfter));
    if (!isTargetAfter) { offsetY = 0; }
  }
  return JSON.stringify({
    x: cx, y: cy,
    isTarget: isTarget,
    occluderHeight: occluderHeight,
    offsetY: offsetY > 0 ? offsetY : cy,
    tag: el.tagName.toLowerCase(),
    text: el.textContent.trim().substring(0, 40)
  });
})()
"""

_FIND_BY_TEXT_JS = r"""
(() => {
  const tag = %s;
  const check = %s;
  const mode = %s;
  const els = document.querySelectorAll(tag || '*');
  for (let i = 0; i < els.length; i++) {
    const el = els[i];
    const text = el.textContent.trim();
    if (mode === 'exact' ? text === check : text.includes(check)) {
      el.scrollIntoView({block: 'center', behavior: 'instant'});
      const rect = el.getBoundingClientRect();
      const cx = Math.round(rect.x + rect.width / 2);
      const cy = Math.round(rect.y + rect.height / 2);
      const hitEl = document.elementFromPoint(cx, cy);
      const isTarget = (hitEl === el || el.contains(hitEl));
      let occluderHeight = 0;
      let offsetY = 0;
      if (!isTarget && hitEl) {
        occluderHeight = Math.round(hitEl.getBoundingClientRect().height);
        offsetY = cy - occluderHeight - 10;
        const hitAfter = document.elementFromPoint(cx, offsetY);
        const isTargetAfter = (hitAfter === el || el.contains(hitAfter));
        if (!isTargetAfter) { offsetY = 0; }
      }
      return JSON.stringify({
        x: cx, y: cy,
        isTarget: isTarget,
        occluderHeight: occluderHeight,
        offsetY: offsetY > 0 ? offsetY : cy,
        found: true,
        index: i,
        tag: el.tagName.toLowerCase(),
        text: text.substring(0, 40)
      });
    }
  }
  return JSON.stringify({found: false, error: 'no element with matching text'});
})()
"""

_FIND_AND_SCROLL_JS = r"""
(() => {
  const sel = %s;
  const idx = %s;
  const els = document.querySelectorAll(sel);
  if (!els.length) return JSON.stringify({error: 'no elements for selector', count: 0});
  const targetIdx = (idx === 'last') ? els.length - 1 : parseInt(idx);
  if (targetIdx < 0 || targetIdx >= els.length) return JSON.stringify({error: 'index out of range', count: els.length});
  const el = els[targetIdx];
  el.scrollIntoView({block: 'center', behavior: 'instant'});
  const rect = el.getBoundingClientRect();
  const cx = Math.round(rect.x + rect.width / 2);
  const cy = Math.round(rect.y + rect.height / 2);
  const hitEl = document.elementFromPoint(cx, cy);
  const isTarget = (hitEl === el || el.contains(hitEl));
  let occluderHeight = 0;
  let offsetY = 0;
  if (!isTarget && hitEl) {
    occluderHeight = Math.round(hitEl.getBoundingClientRect().height);
    offsetY = cy - occluderHeight - 10;
    const hitAfter = document.elementFromPoint(cx, offsetY);
    const isTargetAfter = (hitAfter === el || el.contains(hitAfter));
    if (!isTargetAfter) { offsetY = 0; }
  }
  return JSON.stringify({
    x: cx, y: cy,
    isTarget: isTarget,
    occluderHeight: occluderHeight,
    offsetY: offsetY > 0 ? offsetY : cy,
    tag: el.tagName.toLowerCase(),
    text: el.textContent.trim().substring(0, 40),
    total: els.length
  });
})()
"""


def run_steps(cli, config):
    """执行步骤序列, 支持 branch 条件跳转和 MAX_STEPS/MAX_EXECUTIONS 安全限制"""
    result_data = {
        "timestamp": datetime.now().isoformat(),
        "url": "",
        "download_url": None,
        "download_urls": [],
        "status": "started",
        "error": None,
        "step_log": [],
    }

    steps = config.get("STEPS", [])
    if not steps:
        result_data["status"] = "failed"
        result_data["error"] = "STEPS not configured — please define STEPS in config.yaml"
        return result_data

    variables = {}

    max_executions = min(config.get("MAX_EXECUTIONS", 500), 1000)
    max_steps = min(config.get("MAX_STEPS", 100), 200)

    if len(steps) > max_steps:
        result_data["status"] = "failed"
        result_data["error"] = "STEPS count (%d) exceeds MAX_STEPS (%d)" % (len(steps), max_steps)
        return result_data

    i = 0
    execution_count = 0

    while i < len(steps) and execution_count < max_executions:
        step = steps[i]
        action = step.get("action", "")
        step_name = step.get("name", "")
        step_display = "%s/%s" % (i + 1, step_name) if step_name else str(i + 1)
        log.info("=== Step %s: %s (execution #%d) ===", step_display, action, execution_count + 1)

        success, output, next_step_idx = execute_step(cli, step, variables, config, steps)

        result_data["step_log"].append({
            "step": i + 1,
            "name": step.get("name", ""),
            "action": action,
            "success": success,
            "output": str(output)[:200] if output else "",
        })

        if action == "save":
            collect_download_urls(result_data, variables)
            save_result(result_data, config)

        if not success and step.get("on_fail", "abort") == "abort":
            result_data["status"] = "failed"
            result_data["error"] = str(output)
            return result_data

        if next_step_idx is not None:
            i = next_step_idx
            execution_count += 1
            continue

        i += 1
        execution_count += 1

    if execution_count >= max_executions:
        result_data["status"] = "failed"
        result_data["error"] = "Max executions (%d) reached, possible infinite loop" % max_executions
        collect_download_urls(result_data, variables)
        save_result(result_data, config)
        return result_data

    if "save" not in [s.get("action") for s in steps]:
        collect_download_urls(result_data, variables)
        result_data["status"] = "success" if result_data["download_urls"] else "no_download_found"
        save_result(result_data, config)

    return result_data


def collect_download_urls(result_data, variables):
    urls = variables.get("download_urls", [])
    if isinstance(urls, str):
        try:
            urls = json.loads(urls)
        except (json.JSONDecodeError, TypeError):
            urls = [urls]
    if not isinstance(urls, list):
        urls = [urls] if urls else []
    result_data["download_urls"] = list(dict.fromkeys(urls))
    result_data["download_url"] = result_data["download_urls"][0] if result_data["download_urls"] else None
    result_data["status"] = "success" if result_data["download_urls"] else "no_download_found"


def execute_step(cli, step, variables, config, steps):
    action = step.get("action", "")
    on_fail = step.get("on_fail", "abort")
    default_delay = config.get("STEP_DELAY", 2)

    try:
        resolved = resolve_variables(step, variables)

        if action == "navigate":
            output = cli.navigate(resolved["url"])
            time.sleep(step.get("delay", default_delay))
            return True, output, None

        elif action == "fill":
            match_info = _resolve_match_to_selector(step)
            default_delay = config.get("STEP_DELAY", 2)

            if match_info:
                fill_content = resolved.get("content", "")

                if match_info["type"] == "css":
                    selector = match_info["selector"]
                    log.info("Fill by match: %s=%s → selector: %s, content: %s", step.get("match"), step.get("value", ""), selector, fill_content)
                    scroll_js = _SCROLL_VIEW_JS % (_js_escape(selector), "null")
                    scroll_result = cli.evaluate(scroll_js)
                    scroll_info = json.loads(_strip_cli_hint(scroll_result.strip()))
                    if "error" not in scroll_info:
                        time.sleep(0.3)
                        cli.click(selector)
                        time.sleep(0.2)
                    cli.fill(selector, fill_content)
                    time.sleep(step.get("delay", 0.5))
                    return True, "", None

                elif match_info["type"] == "js_text":
                    value = match_info["value"]
                    tag = match_info.get("tag", "")
                    match_mode = match_info.get("match_mode", "exact")
                    log.info("Fill by text match: value=%s, tag=%s, content=%s, match_mode=%s", value, tag, fill_content, match_mode)

                    safe_value = _js_escape(value)
                    safe_tag = _js_escape(tag) if tag else "''"
                    safe_content = _js_escape(fill_content)
                    text_check = "el.textContent.trim() === %s" % safe_value if match_mode == "exact" else "el.textContent.trim().includes(%s)" % safe_value

                    fill_js = (
                        "(() => {"
                        "  const els = document.querySelectorAll(%s || '*');"
                        "  for (const el of els) {"
                        "    if (%s) {"
                        "      if (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA') {"
                        "        el.value = %s;"
                        "        el.dispatchEvent(new Event('input', {bubbles: true}));"
                        "        el.dispatchEvent(new Event('change', {bubbles: true}));"
                        "        return 'filled by text match';"
                        "      }"
                        "      return 'ERROR:element found but not an input';"
                        "    }"
                        "  }"
                        "  return 'ERROR:no element with matching text found';"
                        "})()"
                    ) % (safe_tag, text_check, safe_content)
                    result = cli.evaluate(fill_js)
                    if "ERROR" in result:
                        on_fail = step.get("on_fail", "abort")
                        return _handle_fail(on_fail, result), result, None
                    time.sleep(step.get("delay", 0.5))
                    return True, result, None

            params = resolved.get("params", {})
            if not params and resolved.get("selector"):
                params = {resolved["selector"]: resolved.get("content", "")}
            for selector, value in params.items():
                scroll_js = _SCROLL_VIEW_JS % (_js_escape(selector), "null")
                scroll_result = cli.evaluate(scroll_js)
                scroll_info = json.loads(_strip_cli_hint(scroll_result.strip()))
                if "error" not in scroll_info:
                    time.sleep(0.3)
                    cli.click(selector)
                    time.sleep(0.2)
                cli.fill(selector, value)
                time.sleep(step.get("delay", 0.5))
            return True, "", None

        elif action == "click":
            success, output = execute_click(cli, resolved, step, config)
            return success, output, None

        elif action == "hover":
            selector = resolved.get("selector", "")
            if not selector:
                return True, "skip_empty_selector", None
            scroll_js = _SCROLL_VIEW_JS % (_js_escape(selector), "null")
            scroll_result = cli.evaluate(scroll_js)
            scroll_info = json.loads(_strip_cli_hint(scroll_result.strip()))
            if "error" in scroll_info:
                return False, scroll_info["error"], None
            time.sleep(0.3)
            output = cli.hover(selector)
            time.sleep(step.get("delay", default_delay))
            return True, output, None

        elif action == "click_at":
            output = cli.click_at(int(resolved["x"]), int(resolved["y"]))
            time.sleep(step.get("delay", default_delay))
            return True, output, None

        elif action == "type_text":
            output = cli.type_text(resolved["text"], resolved.get("submit_key"))
            time.sleep(step.get("delay", default_delay))
            return True, output, None

        elif action == "press_key":
            output = cli.press_key(resolved["key"])
            time.sleep(step.get("delay", default_delay))
            return True, output, None

        elif action == "wait":
            success, output = execute_wait(cli, resolved, step, config)
            return success, output, None

        elif action == "evaluate":
            output = cli.evaluate(resolved["expr"])
            if step.get("save_to"):
                variables[step["save_to"]] = output.strip()
            return True, output, None

        elif action == "extract":
            urls = execute_extract(cli, resolved, step, variables, config)
            if step.get("save_to"):
                variables[step["save_to"]] = urls
            return True, urls, None

        elif action == "loop":
            success, output = execute_loop(cli, resolved, step, variables, config)
            return success, output, None

        elif action == "screenshot":
            path = step.get("output") or os.path.join(
                config["OUTPUT_DIR"],
                "result_%s.png" % datetime.now().strftime("%Y%m%d_%H%M%S"),
            )
            cli.screenshot(path)
            return True, path, None

        elif action == "snapshot":
            if step.get("format") == "json":
                output = cli.snapshot_json()
            else:
                output = cli.snapshot_text()
            if step.get("save_to"):
                variables[step["save_to"]] = output
            return True, output, None

        elif action == "new_page":
            output = cli.new_page(resolved["url"])
            return True, output, None

        elif action == "list_pages":
            output = cli.list_pages()
            return True, output, None

        elif action == "save":
            return True, "save_pending", None

        elif action == "branch":
            return execute_branch(cli, resolved, step, variables, config, steps)

        else:
            log.error("未知 action: %s", action)
            return _handle_fail(on_fail, "unknown action: %s" % action), action, None

    except RuntimeError as e:
        msg = str(e)
        return _handle_fail(on_fail, msg), msg, None


def _strip_cli_hint(text):
    """chrome-devtools evaluate 输出可能包含 [HINT] 行, 需剥离后再解析 JSON"""
    lines = text.split('\n')
    clean_lines = [l for l in lines if not l.strip().startswith('[HINT')]
    return '\n'.join(clean_lines).strip()


def _smart_click_at(cli, selector, index_val=None, label=""):
    """scrollIntoView + 遮挡检测 + 偏移重试 → cli.click_at()

    index_val: None=querySelector第一个, 'last'=最后一个, 数字=第N个(0-based)
    label: 日志标识 (如 "click by match:text")
    """
    safe_sel = _js_escape(selector)
    idx_arg = _js_escape(str(index_val)) if index_val is not None else "null"

    js = _FIND_AND_SCROLL_JS % (safe_sel, idx_arg)
    result = cli.evaluate(js)
    info = json.loads(_strip_cli_hint(result.strip()))

    if "error" in info:
        log.warning("%s: %s (selector=%s)", label, info["error"], selector)
        return False, info["error"]

    x, y = info["x"], info["y"]

    if info.get("isTarget"):
        log.info("%s: CDP click (%d, %d) on <%s> — 唯一命中 ✓", label, x, y, info.get("tag", ""))
    else:
        occluder = info.get("occluderHeight", 0)
        adjusted_y = info.get("offsetY", y)
        if adjusted_y != y and adjusted_y > 0:
            log.warning("%s: 中心点(%d,%d)被遮挡(高度%d), 偏移至(%d,%d)", label, x, y, occluder, x, adjusted_y)
            y = adjusted_y
        else:
            log.warning("%s: 中心点(%d,%d)被遮挡, 无法自动偏移 — 继续点击原坐标", label, x, y)

    time.sleep(0.3)
    output = cli.click_at(x, y)
    detail = "%s: clicked <%s> at (%d,%d)" % (label, info.get("tag", ""), x, y)
    log.info(detail)
    return True, detail


def _smart_click_at_by_text(cli, value, tag, match_mode, label="click by text match"):
    """JS 查找文本匹配元素 → scrollIntoView + 遮挡检测 → cli.click_at()"""
    safe_tag = _js_escape(tag) if tag else "''"
    safe_value = _js_escape(value)
    mode_arg = _js_escape(match_mode)

    js = _FIND_BY_TEXT_JS % (safe_tag, safe_value, mode_arg)
    result = cli.evaluate(js)
    info = json.loads(_strip_cli_hint(result.strip()))

    if not info.get("found"):
        log.warning("%s: %s", label, info.get("error", "not found"))
        return False, info.get("error", "no element with matching text")

    x, y = info["x"], info["y"]

    if info.get("isTarget"):
        log.info("%s: CDP click (%d, %d) on <%s> text='%s' — 唯一命中 ✓", label, x, y, info.get("tag", ""), info.get("text", ""))
    else:
        occluder = info.get("occluderHeight", 0)
        adjusted_y = info.get("offsetY", y)
        if adjusted_y != y and adjusted_y > 0:
            log.warning("%s: 中心点(%d,%d)被遮挡(高度%d), 偏移至(%d,%d)", label, x, y, occluder, x, adjusted_y)
            y = adjusted_y
        else:
            log.warning("%s: 中心点(%d,%d)被遮挡, 无法自动偏移 — 继续点击原坐标", label, x, y)

    time.sleep(0.3)
    output = cli.click_at(x, y)
    detail = "%s: clicked <%s> text='%s' at (%d,%d)" % (label, info.get("tag", ""), info.get("text", ""), x, y)
    log.info(detail)
    return True, detail


def execute_click(cli, resolved, step, config):
    default_delay = config.get("STEP_DELAY", 2)
    match_info = _resolve_match_to_selector(step)

    if match_info:
        if resolved.get("selector"):
            log.warning("Click step has both match and selector; selector ignored")

        if match_info["type"] == "css":
            selector = match_info["selector"]
            index = step.get("index", 1)
            log.info("Click by match: %s=%s → selector: %s, index: %s", step.get("match"), step.get("value", ""), selector, index)

            if str(index) == "last":
                success, output = _smart_click_at(cli, selector, index_val="last", label="click by match (last)")
                time.sleep(step.get("delay", default_delay))
                return success, output

            elif index != 1:
                idx = int(index) - 1
                success, output = _smart_click_at(cli, selector, index_val=str(idx), label="click by match (index %d)" % index)
                time.sleep(step.get("delay", default_delay))
                return success, output

            else:
                safe_sel = _js_escape(selector)
                idx_arg = "null"
                js = _SCROLL_VIEW_JS % (safe_sel, idx_arg)
                result = cli.evaluate(js)
                info = json.loads(_strip_cli_hint(result.strip()))
                if "error" in info:
                    return False, info["error"]
                time.sleep(0.3)
                output = cli.click(selector)
                log.info("click by match: selector=%s → CDP click ✓", selector)
                time.sleep(step.get("delay", default_delay))
                return True, output

        elif match_info["type"] == "js_text":
            value = match_info["value"]
            tag = match_info.get("tag", "")
            match_mode = match_info.get("match_mode", "exact")
            log.info("Click by text match: value=%s, tag=%s, match_mode=%s", value, tag, match_mode)
            success, output = _smart_click_at_by_text(cli, value, tag, match_mode)
            time.sleep(step.get("delay", default_delay))
            return success, output

    selector = resolved.get("selector", "")
    if not selector:
        return True, "skip_empty_selector"

    index = step.get("index", 1)
    log.info("Click by selector: %s, index: %s", selector, index)

    if str(index) == "last":
        success, output = _smart_click_at(cli, selector, index_val="last", label="click selector (last)")
        time.sleep(step.get("delay", default_delay))
        return success, output

    elif index != 1:
        idx = int(index) - 1
        success, output = _smart_click_at(cli, selector, index_val=str(idx), label="click selector (index %d)" % index)
        time.sleep(step.get("delay", default_delay))
        return success, output

    else:
        safe_sel = _js_escape(selector)
        idx_arg = "null"
        js = _SCROLL_VIEW_JS % (safe_sel, idx_arg)
        result = cli.evaluate(js)
        info = json.loads(_strip_cli_hint(result.strip()))
        if "error" in info:
            return False, info["error"]
        time.sleep(0.3)
        output = cli.click(selector)
        log.info("click selector: %s → CDP click ✓", selector)
        time.sleep(step.get("delay", default_delay))
        return True, output


def execute_wait(cli, resolved, step, config):
    strategy = step.get("strategy", "timeout")
    timeout = step.get("timeout", 15000)
    timeout_sec = timeout / 1000

    if strategy == "text":
        value = resolved.get("value", "")
        cli.wait_for(value, timeout_ms=timeout)
        return True, value

    elif strategy == "element":
        selector = resolved.get("selector", "")
        safe_selector = _js_escape(selector)
        js = "document.querySelector(%s) !== null" % safe_selector
        deadline = time.time() + timeout_sec
        while time.time() < deadline:
            result = cli.evaluate(js).strip()
            if result == "true":
                return True, selector
            time.sleep(0.5)
        return False, "element %s not found within %dms" % (selector, timeout)

    elif strategy == "url_change":
        current_url_js = "window.location.href"
        original = cli.evaluate(current_url_js).strip()
        deadline = time.time() + timeout_sec
        while time.time() < deadline:
            current = cli.evaluate(current_url_js).strip()
            if current != original:
                return True, current
            time.sleep(0.5)
        return False, "URL unchanged within %dms" % timeout

    elif strategy == "js":
        expr = resolved.get("expr", "")
        deadline = time.time() + timeout_sec
        while time.time() < deadline:
            result = cli.evaluate(expr).strip()
            if result and result not in ("false", "null", "undefined", "0", "NaN", ""):
                return True, result
            time.sleep(0.5)
        return False, "JS condition not met within %dms" % timeout

    elif strategy == "timeout":
        time.sleep(timeout_sec)
        return True, "waited %dms" % timeout

    return False, "unknown wait strategy: %s" % strategy


def execute_extract(cli, resolved, step, variables, config):
    strategy = step.get("strategy", "auto")
    urls = []

    if strategy in ("css", "auto"):
        selector = resolved.get("selector", "")
        if selector:
            safe_selector = _js_escape(selector)
            href_js = (
                "(() => {"
                "  const els = document.querySelectorAll(%s);"
                "  return JSON.stringify([...els].map(e => e.href).filter(Boolean));"
                "})()"
            ) % safe_selector
            href_result = cli.evaluate(href_js)
            try:
                raw = href_result.strip()
                if raw.startswith('"') and raw.endswith('"'):
                    raw = json.loads(raw)
                parsed = json.loads(raw) if isinstance(raw, str) else raw
                if isinstance(parsed, list):
                    urls.extend(parsed)
            except json.JSONDecodeError:
                log.warning("CSS extract failed, raw: %s", href_result[:200])

    if strategy in ("js", "auto") and not urls:
        expr = resolved.get("expr", "")
        if expr:
            js_result = cli.evaluate(expr).strip()
            if js_result and js_result.startswith("http"):
                urls.append(js_result)
            elif js_result:
                try:
                    parsed = json.loads(js_result)
                    if isinstance(parsed, list):
                        urls.extend(parsed)
                except (json.JSONDecodeError, TypeError):
                    pass

    if strategy == "semantic" or (strategy == "auto" and not urls):
        tree = cli.snapshot_text()
        url_pattern = re.compile(r'https?://[^\s"\'<>]+(?:download|file|attachment)[^\s"\'<>]*', re.IGNORECASE)
        found = url_pattern.findall(tree)
        if found:
            urls.extend(found)
        else:
            try:
                tree_json = cli.snapshot_json()
                nodes = tree_json.get("nodes", [])
                for node in nodes:
                    name_val = node.get("name", {}).get("value", "")
                    if "下载" in name_val or "download" in name_val.lower():
                        nearby_js = (
                            "(() => {"
                            "  const links = document.querySelectorAll('a[href]');"
                            "  const urls = [];"
                            "  for (const a of links) {"
                            "    if (a.textContent.includes('下载') ||"
                            "        a.textContent.toLowerCase().includes('download') ||"
                            "        a.href.includes('download')) {"
                            "      urls.push(a.href);"
                            "    }"
                            "  }"
                            "  return JSON.stringify(urls);"
                            "})()"
                        )
                        nearby_result = cli.evaluate(nearby_js)
                        try:
                            raw = nearby_result.strip()
                            if raw.startswith('"') and raw.endswith('"'):
                                raw = json.loads(raw)
                            parsed = json.loads(raw) if isinstance(raw, str) else raw
                            if isinstance(parsed, list):
                                urls.extend(parsed)
                        except json.JSONDecodeError:
                            pass
                        break
            except Exception as e:
                log.warning("snapshot JSON parse failed: %s", e)

    return urls


def execute_loop(cli, resolved, step, variables, config):
    condition = step.get("condition", "js")
    max_iterations = step.get("max_iterations", 30)
    interval_sec = step.get("interval", 2000) / 1000
    on_timeout = step.get("on_timeout", "fail")
    each_steps = step.get("each", None)

    for i in range(max_iterations):
        # 执行 each 子步骤 (每轮条件检查前执行)
        if each_steps:
            for sub_step in each_steps:
                sub_action = sub_step.get("action", "")
                log.info("Loop each[%d]: %s", i, sub_action)
                try:
                    success, output, _ = execute_step(cli, sub_step, variables, config, [])
                except RuntimeError as e:
                    log.warning("Loop each[%d] %s failed: %s, skipping", i, sub_action, e)
                    continue
                if sub_step.get("save_to") and output:
                    variables[sub_step["save_to"]] = output.strip() if isinstance(output, str) else output

        if condition == "js":
            result = cli.evaluate(resolved.get("expr", "")).strip()
            if result and result not in ("false", "null", "undefined", "0", "NaN", ""):
                log.info("Loop condition met at iteration %d", i)
                return True, "condition met at iteration %d" % i

        elif condition == "element_exists":
            selector = resolved.get("selector", "")
            safe_selector = _js_escape(selector)
            js = "document.querySelector(%s) !== null" % safe_selector
            result = cli.evaluate(js).strip()
            if result == "true":
                log.info("Loop element found at iteration %d", i)
                return True, "element found at iteration %d" % i

        elif condition == "text_exists":
            value = resolved.get("value", "")
            safe_value = _js_escape(value)
            js = "document.body.textContent.includes(%s)" % safe_value
            result = cli.evaluate(js).strip()
            if result == "true":
                log.info("Loop text found at iteration %d", i)
                return True, "text found at iteration %d" % i

        time.sleep(interval_sec)

    if on_timeout == "fail":
        return False, "loop timeout after %d iterations" % max_iterations
    elif on_timeout == "continue":
        log.warning("Loop timeout, continuing")
        return True, "loop timeout, continuing"
    elif on_timeout == "extract_and_continue":
        urls = execute_extract(cli, resolved, step, variables, config)
        variables["download_urls"] = urls
        return True, "loop timeout, extracted %d urls" % len(urls)

    return False, "loop timeout after %d iterations" % max_iterations


def execute_branch(cli, resolved, step, variables, config, steps):
    def _resolve_goto(goto_value, steps):
        """Resolve goto target: if string, find step by name; if int, use 1-based index."""
        if isinstance(goto_value, str) and not goto_value.isdigit():
            for idx, s in enumerate(steps):
                if s.get("name") == goto_value:
                    return idx
            log.error("branch goto '%s': no step with name '%s'", goto_value, goto_value)
            return None
        target = int(goto_value) - 1
        if target < 0 or target >= len(steps):
            log.error("branch goto %d out of range (1-%d)", int(goto_value), len(steps))
            return None
        return target

    def _eval_and_jump(expr, target_value):
        expr = _replace_vars(expr, variables)
        result = cli.evaluate(expr).strip()
        if result and result not in ("false", "null", "undefined", "0", "NaN", ""):
            if target_value is not None:
                target = _resolve_goto(target_value, steps)
                if target is None:
                    return True, "branch target not found", None, True
                log.info("Branch condition met: '%s' → %s", expr[:50], target_value)
                return True, "branched to %s" % target_value, target, False
            log.info("Branch condition met: '%s' (no target, continuing)", expr[:50])
            return True, "condition met, continuing", None, False
        return None

    # New format: branches list of clause dicts [{if/elif/else: ...}]
    branches_list = step.get("branches", None)
    if branches_list is not None:
        has_if = False
        for clause in branches_list:
            if "if" in clause:
                has_if = True
                result = _eval_and_jump(clause["if"], clause.get("then", None))
                if result is not None:
                    return result[:3]
            elif "elif" in clause:
                result = _eval_and_jump(clause["elif"], clause.get("then", None))
                if result is not None:
                    return result[:3]
            elif "else" in clause:
                target_value = clause["else"]
                target = _resolve_goto(target_value, steps)
                if target is None:
                    return True, "branch else not found", None, True
                log.info("No branch condition met → else %s", target_value)
                return True, "else branched to %s" % target_value, target
        if not has_if:
            log.error("branches list has no 'if' clause")
            return True, "branches missing if clause", None, True
        log.info("No branch condition met, no else, continuing")
        return True, "no match, continuing", None

    # No branches key found — invalid branch step
    log.error("branch step missing 'branches' key")
    return True, "branch missing branches", None, True


def resolve_variables(step, variables):
    resolved = {}
    for key, value in step.items():
        if isinstance(value, str):
            resolved[key] = _replace_vars(value, variables)
        elif isinstance(value, dict):
            resolved[key] = {k: _replace_vars(v, variables) if isinstance(v, str) else v for k, v in value.items()}
        else:
            resolved[key] = value
    return resolved


def _replace_vars(text, variables):
    for var_name, var_value in variables.items():
        text = text.replace("${%s}" % var_name, str(var_value))
    return text


def _handle_fail(on_fail, error_msg):
    if on_fail == "skip":
        log.warning("Step failed but skipped: %s", error_msg)
        return False
    if on_fail == "abort":
        raise RuntimeError(error_msg)
    match = re.match(r"retry\((\d+)\)", on_fail)
    if match:
        log.warning("Step failed: %s (retry mode not yet implemented in single-step scope)", error_msg)
        raise RuntimeError(error_msg)
    raise RuntimeError(error_msg)


def _resolve_match_to_selector(step):
    """Convert match parameter to CSS selector or JS locator info.

    Returns:
        None — no match specified, use regular selector
        {"type": "css", "selector": "..."} — can use cli.click(selector) directly
        {"type": "js_text", "value": "...", "tag": "..."} — needs JS evaluation
    """
    match = step.get("match")
    value = step.get("value", "")
    tag = step.get("tag", "")
    match_mode = step.get("match_mode", "exact")

    if not match:
        return None

    # Attribute match types → CSS attribute selectors
    attr_map = {
        "href": "href",
        "aria_label": "aria-label",
        "aria-label": "aria-label",
        "name": "name",
        "placeholder": "placeholder",
    }

    if match in attr_map:
        attr = attr_map[match]
        prefix = tag if tag else ""
        # CSS attribute selector: exact (=) or contains (*=)
        op = "*=" if match_mode == "contains" else "="
        selector = "%s[%s%s'%s']" % (prefix, attr, op, value)
        return {"type": "css", "selector": selector}

    elif match == "text":
        # Can't match by text in CSS — need JS
        return {"type": "js_text", "value": value, "tag": tag, "match_mode": match_mode}

    return None


def _js_escape(value):
    return json.dumps(value)


def run_steps_with_retry(cli, config):
    """带重试的步骤执行 — 最多 MAX_RETRIES 次"""
    max_retries = config.get("MAX_RETRIES", 3)
    for attempt in range(1, max_retries + 1):
        log.info("尝试第 %d/%d 次", attempt, max_retries)
        result = run_steps(cli, config)
        if result["status"] in ("success", "no_download_found"):
            return result
        if attempt < max_retries:
            delay = config.get("STEP_DELAY", 2) * 2
            log.warning("第 %d 次失败, %d 秒后重试...", attempt, delay)
            time.sleep(delay)
    log.error("所有 %d 次尝试均失败", max_retries)
    return result