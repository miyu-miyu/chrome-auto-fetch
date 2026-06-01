"""
Discovery 模式 — 分析页面结构, 帮助填写配置
"""

import json
import os
import re
import time
import logging

log = logging.getLogger("chrome_auto_fetch")


def _strip_cli_hint(text):
    """chrome-devtools evaluate 输出可能包含 [HINT] 行, 需剥离后再解析 JSON"""
    # 移除所有 [HINT: ...] 行
    lines = text.split('\n')
    clean_lines = [l for l in lines if not l.strip().startswith('[HINT')]
    return '\n'.join(clean_lines).strip()

# Accessibility Tree 中交互角色的列表
INTERACTIVE_ROLES = [
    "button", "link", "textbox", "combobox", "searchbox",
    "menuitem", "tab", "checkbox", "radio", "slider",
    "spinbutton", "switch", "treeitem",
]

# Accessibility role → HTML tag 的常见映射
ROLE_TO_TAG = {
    "button": "button",
    "link": "a",
    "textbox": "input",
    "combobox": "select",
    "searchbox": "input",
    "checkbox": "input",
    "radio": "input",
    "slider": "input",
    "spinbutton": "input",
    "switch": "button",
    "menuitem": "li",
    "tab": "button",
    "treeitem": "li",
}


# 增强版 JS 提取脚本: 为每个交互元素计算唯一 CSS 选择器 + 提取完整属性
ELEMENTS_JS = r"""
(() => {
    function computeSelector(el) {
        // 优先使用 id
        if (el.id) return '#' + el.id;
        // 其次 name
        const tag = el.tagName.toLowerCase();
        if (el.name) return tag + '[name="' + el.name + '"]';
        // 其次 class (取第一个有意义的 class)
        if (el.className && typeof el.className === 'string') {
            const classes = el.className.trim().split(/\s+/).filter(c =>
                c && !c.match(/^(devui|ng-|cdk|mat-|Mui)/i) && c.length > 1
            );
            if (classes.length > 0) return tag + '.' + classes[0];
        }
        // 最后: 构建 nth-child 路径 (最多 4 层)
        const path = [];
        let current = el;
        let depth = 0;
        while (current && current !== document.body && depth < 4) {
            let seg = current.tagName.toLowerCase();
            // 附加第一个有意义的 class
            if (current.className && typeof current.className === 'string') {
                const cls = current.className.trim().split(/\s+/).filter(c =>
                    c && !c.match(/^(devui|ng-|cdk|mat-|Mui)/i) && c.length > 1
                );
                if (cls.length > 0) seg += '.' + cls[0];
            }
            // nth-of-type
            const parent = current.parentElement;
            if (parent) {
                const siblings = Array.from(parent.children).filter(
                    c => c.tagName === current.tagName
                );
                if (siblings.length > 1) {
                    const idx = siblings.indexOf(current) + 1;
                    seg += ':nth-of-type(' + idx + ')';
                }
            }
            path.unshift(seg);
            current = parent;
            depth++;
        }
        return path.join(' > ');
    }

    const results = [];
    const els = document.querySelectorAll(
        'input, select, button, textarea, a[href], [role="button"], [role="link"], [role="searchbox"], [role="combobox"]'
    );
    for (const el of els) {
        // 跳过不可见元素
        const rect = el.getBoundingClientRect();
        if (rect.width === 0 && rect.height === 0) continue;

        const text = (el.textContent || el.value || el.placeholder || '').substring(0, 80).trim();
        const selector = computeSelector(el);

        results.push({
            tag: el.tagName.toLowerCase(),
            selector: selector,
            text: text,
            id: el.id || '',
            className: (el.className && typeof el.className === 'string')
                ? el.className.trim().split(/\s+/).slice(0, 5).join(' ') : '',
            name_attr: el.name || '',
            type: el.type || '',
            href: el.href ? el.href.substring(0, 120) : '',
            role: el.getAttribute('role') || '',
            aria_label: el.getAttribute('aria-label') || '',
            placeholder: el.placeholder || '',
            value: el.value || '',
            offset_parent: el.offsetParent !== null,
        });
    }
    return JSON.stringify(results);
})()
"""

# 用于验证选择器唯一性的 JS 脚本
VERIFY_SELECTORS_JS = r"""
(() => {
    const results = {};
    const selectors = %s;
    for (const sel of selectors) {
        try {
            const count = document.querySelectorAll(sel).length;
            results[sel] = count;
        } catch (e) {
            results[sel] = -1;  // invalid selector
        }
    }
    return JSON.stringify(results);
})()
"""


def _extract_a11y_interactive_nodes(tree_json):
    """从 Accessibility Tree JSON 中提取交互节点列表。

    返回: [{role, name, nodeId, backendDOMNodeId}, ...]
    """
    nodes = tree_json.get("nodes", [])
    interactive = []
    for n in nodes:
        if n.get("ignored", False):
            continue
        role = n.get("role", {}).get("value", "")
        if role not in INTERACTIVE_ROLES:
            continue
        name = n.get("name", {}).get("value", "")
        nid = n.get("nodeId", "")
        bid = n.get("backendDOMNodeId", "")
        interactive.append({
            "role": role,
            "name": name,
            "nodeId": nid,
            "backendDOMNodeId": bid,
        })
    return interactive


def _match_a11y_to_dom(a11y_nodes, dom_elements):
    """将 Accessibility Tree 交互节点与 DOM 元素交叉匹配。

    匹配策略:
    1. 精确匹配: role 映射到 tag, name 完全等于 text (或 aria_label)
    2. 子串匹配: name 包含在 text 中, 或 text 包含在 name 中
    3. 宽松匹配: role 映射到 tag, 没有文字匹配但 tag 相同

    返回: [{a11y_role, a11y_name, dom_tag, dom_selector, dom_text, match_quality, ...}, ...]
    """
    mappings = []
    used_dom_indices = set()

    # 第一轮: 精确匹配
    for a11y in a11y_nodes:
        expected_tags = _role_to_expected_tags(a11y["role"])
        a11y_name = a11y["name"].strip()

        best_match_idx = None
        best_quality = 0

        for i, dom in enumerate(dom_elements):
            if i in used_dom_indices:
                continue
            if dom["tag"] not in expected_tags:
                continue

            quality = 0
            # aria-label 精确匹配 (最高优先级)
            if a11y_name and dom.get("aria_label") and a11y_name == dom["aria_label"].strip():
                quality = 3
            # text 精确匹配
            elif a11y_name and dom.get("text") and a11y_name == dom["text"].strip():
                quality = 3
            # placeholder 精确匹配 (textbox 的 name 可能来自 placeholder)
            elif a11y_name and dom.get("placeholder") and a11y_name == dom["placeholder"].strip():
                quality = 3
            # name 属性精确匹配
            elif a11y_name and dom.get("name_attr") and a11y_name == dom["name_attr"].strip():
                quality = 2
            # id 精确匹配 (某些 a11y name 来自 id)
            elif a11y_name and dom.get("id") and a11y_name == dom["id"].strip():
                quality = 2
            # 子串匹配: a11y_name 包含在 dom.text 中
            elif a11y_name and dom.get("text") and a11y_name in dom["text"]:
                quality = 1
            # 子串匹配: dom.text 包含在 a11y_name 中
            elif a11y_name and dom.get("text") and dom["text"] in a11y_name and len(dom["text"]) > 2:
                quality = 1
            # 没有 name 的 textbox 搜索框匹配 (空 name + input type=text/search)
            elif not a11y_name and dom["tag"] == "input" and dom.get("type") in ("text", "search", ""):
                quality = 1

            if quality > best_quality:
                best_quality = quality
                best_match_idx = i

        if best_match_idx is not None and best_quality > 0:
            dom = dom_elements[best_match_idx]
            used_dom_indices.add(best_match_idx)
            mappings.append({
                "a11y_role": a11y["role"],
                "a11y_name": a11y["name"],
                "a11y_nodeId": a11y["nodeId"],
                "dom_tag": dom["tag"],
                "dom_selector": dom["selector"],
                "dom_text": dom.get("text", ""),
                "dom_id": dom.get("id", ""),
                "dom_className": dom.get("className", ""),
                "dom_type": dom.get("type", ""),
                "dom_href": dom.get("href", ""),
                "dom_placeholder": dom.get("placeholder", ""),
                "dom_aria_label": dom.get("aria_label", ""),
                "dom_name_attr": dom.get("name_attr", ""),
                "match_quality": best_quality,
                "matched": True,
            })
        else:
            mappings.append({
                "a11y_role": a11y["role"],
                "a11y_name": a11y["name"],
                "a11y_nodeId": a11y["nodeId"],
                "dom_tag": "",
                "dom_selector": "",
                "dom_text": "",
                "dom_id": "",
                "dom_className": "",
                "dom_type": "",
                "dom_href": "",
                "dom_placeholder": "",
                "dom_aria_label": "",
                "dom_name_attr": "",
                "match_quality": 0,
                "matched": False,
            })

    # 第二轮: 为未匹配的 DOM 元素生成未映射条目 (用户可能仍需要它们)
    for i, dom in enumerate(dom_elements):
        if i not in used_dom_indices:
            mappings.append({
                "a11y_role": "",
                "a11y_name": "",
                "a11y_nodeId": "",
                "dom_tag": dom["tag"],
                "dom_selector": dom["selector"],
                "dom_text": dom.get("text", ""),
                "dom_id": dom.get("id", ""),
                "dom_className": dom.get("className", ""),
                "dom_type": dom.get("type", ""),
                "dom_href": dom.get("href", ""),
                "dom_placeholder": dom.get("placeholder", ""),
                "dom_aria_label": dom.get("aria_label", ""),
                "dom_name_attr": dom.get("name_attr", ""),
                "match_quality": 0,
                "matched": False,
            })

    return mappings


def _role_to_expected_tags(role):
    """Accessibility role → 可能对应的 HTML tag 集合"""
    mapping = {
        "button": {"button", "a", "input"},
        "link": {"a"},
        "textbox": {"input", "textarea"},
        "combobox": {"select", "input"},
        "searchbox": {"input"},
        "checkbox": {"input"},
        "radio": {"input"},
        "slider": {"input"},
        "spinbutton": {"input"},
        "switch": {"button", "div"},
        "menuitem": {"li", "a", "button", "div"},
        "tab": {"button", "a", "div"},
        "treeitem": {"li", "a", "div"},
    }
    return mapping.get(role, {ROLE_TO_TAG.get(role, "div")})


def _quality_label(q):
    if q >= 3:
        return "精确"
    elif q >= 2:
        return "高"
    elif q >= 1:
        return "模糊"
    return "未匹配"


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

    os.makedirs(config["OUTPUT_DIR"], exist_ok=True)

    # ── Section 1: Accessibility Tree (文本 + JSON) ──
    print("1. Accessibility Tree (前50行):")
    print("-" * 40)
    tree_text = cli.snapshot_text()
    lines = tree_text.strip().split("\n")
    for line in lines[:50]:
        print(line)
    if len(lines) > 50:
        print("\n... 共 %d 行, 已截断显示前50行" % len(lines))

    tree_file = os.path.join(config["OUTPUT_DIR"], "discovery_accessibility_tree.txt")
    with open(tree_file, "w", encoding="utf-8") as f:
        f.write(tree_text)
    print("   完整 Accessibility Tree 已保存: %s (%d 行)" % (tree_file, len(lines)))

    # 同时获取 JSON 格式用于映射
    try:
        tree_json = cli.snapshot_json()
        a11y_nodes = _extract_a11y_interactive_nodes(tree_json)
        print("   Accessibility Tree JSON: 共 %d 个交互节点" % len(a11y_nodes))
    except (RuntimeError, json.JSONDecodeError) as e:
        log.warning("获取 Accessibility Tree JSON 失败: %s", e)
        tree_json = None
        a11y_nodes = []

    # ── Section 2: DOM 可交互元素 (增强版 JS 提取) ──
    print("\n2. 可交互元素 (input/select/button/textarea/a):")
    print("-" * 40)
    dom_elements = []
    result = cli.evaluate(ELEMENTS_JS)
    try:
        raw = _strip_cli_hint(result.strip())
        if raw.startswith('"') and raw.endswith('"'):
            raw = json.loads(raw)
        elements = json.loads(raw) if isinstance(raw, str) else raw
        if isinstance(elements, list):
            dom_elements = elements
            for i, el in enumerate(elements):
                print("  [%d] <%s>  selector: %s" % (i, el.get('tag'), el.get('selector')))
                detail_parts = []
                if el.get("id"):
                    detail_parts.append("id=%s" % el['id'])
                if el.get("name_attr"):
                    detail_parts.append("name=%s" % el['name_attr'])
                if el.get("type") and el.get("tag") == "input":
                    detail_parts.append("type=%s" % el['type'])
                if el.get("placeholder"):
                    detail_parts.append("placeholder=%s" % el['placeholder'][:40])
                if el.get("text"):
                    detail_parts.append("text=%s" % el['text'][:50])
                if el.get("href"):
                    detail_parts.append("href=%s" % el['href'][:60])
                if el.get("aria_label"):
                    detail_parts.append("aria-label=%s" % el['aria_label'])
                if el.get("role"):
                    detail_parts.append("role=%s" % el['role'])
                if detail_parts:
                    print("      %s" % ", ".join(detail_parts))
            print("\n  共找到 %d 个可交互元素" % len(elements))
        else:
            print("  JS 提取结果:", raw[:500])
    except json.JSONDecodeError:
        print("  JS 提取结果 (原始):", result[:500])

    # ── Section 3: Accessibility → CSS 选择器映射表 ──
    print("\n3. Accessibility → CSS 选择器映射表:")
    print("-" * 40)

    if a11y_nodes and dom_elements:
        mappings = _match_a11y_to_dom(a11y_nodes, dom_elements)

        matched_count = sum(1 for m in mappings if m["matched"])
        total_a11y = len(a11y_nodes)

        # 输出映射表 (只显示已匹配和关键的未匹配项)
        print("  %-20s  %-35s  %-8s  %s" % ("Accessibility节点", "CSS 选择器", "匹配度", "补充信息"))
        print()
        for m in mappings:
            a11y_label = "[%s] %s" % (m["a11y_role"], m["a11y_name"][:25] if m["a11y_name"] else "(无名称)")
            if m["matched"]:
                extras = []
                if m["dom_id"]:
                    extras.append("id=" + m["dom_id"])
                if m["dom_type"]:
                    extras.append("type=" + m["dom_type"])
                if m["dom_placeholder"]:
                    extras.append("placeholder=" + m["dom_placeholder"][:30])
                if m["dom_href"]:
                    extras.append("href=" + m["dom_href"][:40])
                print("  %-20s  → %-35s  [%s]  %s" % (
                    a11y_label, m["dom_selector"], _quality_label(m["match_quality"]),
                    ", ".join(extras) if extras else ""
                ))
            elif m["dom_selector"]:
                # 未匹配的 DOM 元素 (可能不在 Accessibility Tree 中但仍可用)
                extras = []
                if m["dom_id"]:
                    extras.append("id=" + m["dom_id"])
                if m["dom_type"]:
                    extras.append("type=" + m["dom_type"])
                print("  %-20s  ← %-35s  [仅DOM]  %s" % (
                    "(未在Tree中)", m["dom_selector"],
                    ", ".join(extras) if extras else ""
                ))
            else:
                print("  %-20s  (未找到对应的 HTML 元素)" % a11y_label)

        print()
        print("  匹配统计: %d/%d Accessibility节点已匹配到DOM元素" % (matched_count, total_a11y))

        # 保存映射表 JSON
        mapping_file = os.path.join(config["OUTPUT_DIR"], "discovery_mapping.json")
        with open(mapping_file, "w", encoding="utf-8") as f:
            json.dump(mappings, f, ensure_ascii=False, indent=2)
        print("  映射表 JSON 已保存: %s" % mapping_file)

        # 验证选择器唯一性
        selectors_to_verify = [m["dom_selector"] for m in mappings if m["dom_selector"]]
        if selectors_to_verify:
            verify_js = VERIFY_SELECTORS_JS % json.dumps(selectors_to_verify)
            try:
                verify_result = cli.evaluate(verify_js)
                raw_v = _strip_cli_hint(verify_result.strip())
                if raw_v.startswith('"') and raw_v.endswith('"'):
                    raw_v = json.loads(raw_v)
                selector_counts = json.loads(raw_v) if isinstance(raw_v, str) else raw_v
                non_unique = {s: c for s, c in selector_counts.items() if c > 1}
                if non_unique:
                    print("\n  ⚠ 以下选择器匹配到多个元素 (非唯一):")
                    for sel, cnt in non_unique.items():
                        print("    %s → 匹配 %d 个元素" % (sel, cnt))
                    print("  建议使用更精确的选择器 (添加 id/name/class 等限定)")
                else:
                    print("  ✓ 所有选择器均唯一匹配")
            except (json.JSONDecodeError, RuntimeError):
                pass

    else:
        print("  (无法生成映射表 — 需要 Accessibility Tree JSON 和 DOM 元素列表)")
        if not a11y_nodes:
            print("  原因: Accessibility Tree JSON 获取失败")
        if not dom_elements:
            print("  原因: DOM 元素 JS 提取失败")

    # ── Section 4: 建议编写 STEPS 配置 ──
    print("\n4. 建议编写 STEPS 配置:")
    print("-" * 40)
    print("  根据上面的映射表, 在 config.yaml 中编写 STEPS 步骤序列:")
    print()
    # 从映射表中提取最关键的元素来生成建议
    key_selectors = []
    if a11y_nodes and dom_elements:
        mappings = _match_a11y_to_dom(a11y_nodes, dom_elements)
        for m in mappings:
            if m["matched"] and m["dom_selector"]:
                if m["a11y_role"] in ("textbox", "searchbox", "combobox"):
                    key_selectors.append(("输入框", m["dom_selector"], m["a11y_name"]))
                elif m["a11y_role"] == "button" and any(
                    kw in (m["a11y_name"] or "").lower()
                    for kw in ["搜索", "search", "提交", "submit", "查询", "login", "登录"]
                ):
                    key_selectors.append(("操作按钮", m["dom_selector"], m["a11y_name"]))

    if key_selectors:
        print("  关键元素提示:")
        for label, sel, name in key_selectors[:6]:
            print("    %s: selector=\"%s\" (Accessibility名称: \"%s\")" % (label, sel, name))
        print()

    print("  STEPS:")
    print("    - action: navigate")
    print("      url: \"%s\"" % config["TARGET_URL"])
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

    # ── Section 5: 页面截图 ──
    screenshot_path = os.path.join(config["OUTPUT_DIR"], "discovery_screenshot.png")
    time.sleep(2)
    cli.screenshot(screenshot_path)
    print("5. 页面截图已保存: %s" % screenshot_path)
    print("   请查看截图确认页面结构\n")