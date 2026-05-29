"""
Discovery 模式 — 分析页面结构, 帮助填写配置
"""

import json
import os
import time
import logging

log = logging.getLogger("chrome_auto_fetch")


def discover(cli, config):
    """交互式探索目标页面, 输出所有可交互元素, 帮助用户确定 CSS 选择器"""
    if not config["TARGET_URL"]:
        print("CONFIG.TARGET_URL 未填写, 请先填入目标网站地址")
        return

    print("\n" + "=" * 60)
    print("  Discovery 模式 — 分析页面结构")
    print("=" * 60 + "\n")

    cli.navigate(config["TARGET_URL"])
    time.sleep(config["STEP_DELAY"])

    print("1. Accessibility Tree (前50行):")
    print("-" * 40)
    tree_text = cli.snapshot_text()
    lines = tree_text.strip().split("\n")
    for line in lines[:50]:
        print(line)
    if len(lines) > 50:
        print("\n... 共 %d 行, 已截断显示前50行" % len(lines))

    tree_file = os.path.join(config["OUTPUT_DIR"], "discovery_accessibility_tree.txt")
    os.makedirs(config["OUTPUT_DIR"], exist_ok=True)
    with open(tree_file, "w", encoding="utf-8") as f:
        f.write(tree_text)
    print("   完整 Accessibility Tree 已保存: %s (%d 行)" % (tree_file, len(lines)))

    print("\n2. 可交互元素 (input/select/button/textarea/a):")
    print("-" * 40)
    elements_js = r"""
    (() => {
        const results = [];
        const selectors = [
            ['input', 'input[type], input[name], input[id], input.placeholder'],
            ['select', 'select[name], select[id]'],
            ['button', 'button[type], button[id], button.class'],
            ['textarea', 'textarea[name], textarea[id]'],
            ['a', 'a[href]'],
        ];
        for (const [tag, desc] of selectors) {
            const els = document.querySelectorAll(tag);
            for (const el of els) {
                const selector = el.id ? '#' + el.id :
                    el.name ? tag + '[name="' + el.name + '"]' :
                    el.className ? tag + '.' + el.className.split(' ')[0] :
                    tag;
                const text = el.textContent || el.value || el.placeholder || el.href || '';
                results.push({
                    tag: tag,
                    selector: selector,
                    text: text.substring(0, 60),
                    type: el.type || '',
                    name: el.name || '',
                    id: el.id || '',
                    href: el.href || '',
                });
            }
        }
        return JSON.stringify(results);
    })()
    """
    result = cli.evaluate(elements_js)
    try:
        raw = result.strip()
        if raw.startswith('"') and raw.endswith('"'):
            raw = json.loads(raw)
        elements = json.loads(raw) if isinstance(raw, str) else raw
        if isinstance(elements, list):
            for i, el in enumerate(elements):
                print("  [%d] <%s>  selector: %s" % (i, el.get('tag'), el.get('selector')))
                detail_parts = []
                if el.get("id"):
                    detail_parts.append("id=%s" % el['id'])
                if el.get("name"):
                    detail_parts.append("name=%s" % el['name'])
                if el.get("type"):
                    detail_parts.append("type=%s" % el['type'])
                if el.get("text"):
                    detail_parts.append("text=%s" % el['text'])
                if el.get("href"):
                    detail_parts.append("href=%s" % el['href'][:80])
                if detail_parts:
                    print("      %s" % ", ".join(detail_parts))
            print("\n  共找到 %d 个可交互元素" % len(elements))
        else:
            print("  JS 提取结果:", raw[:500])
    except json.JSONDecodeError:
        print("  JS 提取结果 (原始):", result[:500])

    print("\n3. 建议编写 STEPS 配置:")
    print("-" * 40)
    print("  根据上面的元素列表, 在 config.yaml 中编写 STEPS 步骤序列:")
    print()
    print("  STEPS:")
    print("    - action: navigate")
    print("      url: \"<目标页面URL>\"")
    print("    - action: fill")
    print("      params:")
    print("        \"<输入框选择器>\": \"<填入值>\"")
    print("    - action: click")
    print("      selector: \"<搜索按钮选择器>\"")
    print("    - action: wait")
    print("      strategy: element")
    print("      selector: \"<结果区域选择器>\"")
    print("    - action: click")
    print("      selector: \"<结果链接选择器>\"")
    print("    - action: extract")
    print("      strategy: css")
    print("      selector: \"<下载链接选择器>\"")
    print("      save_to: \"download_urls\"")
    print("    - action: save")
    print()

    screenshot_path = os.path.join(config["OUTPUT_DIR"], "discovery_screenshot.png")
    os.makedirs(config["OUTPUT_DIR"], exist_ok=True)
    time.sleep(2)
    cli.screenshot(screenshot_path)
    print("4. 页面截图已保存: %s" % screenshot_path)
    print("   请查看截图确认页面结构\n")