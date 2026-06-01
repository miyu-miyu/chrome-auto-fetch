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


# 增强版 JS 提取脚本: 为每个交互元素计算多级 CSS 选择器候选列表 + 提取完整属性
ELEMENTS_JS = r"""
(() => {
    // 框架类名过滤规则
    const FRAMEWORK_CLASS_RE = /^(devui|ng-|cdk|mat-|Mui)/i;
    // 角色相关关键词 (用于优先排序 class)
    const ROLE_KEYWORDS = ['search', 'btn', 'button', 'card', 'title', 'nav', 'link', 'input', 'form', 'modal', 'dialog', 'tab', 'menu', 'icon', 'logo', 'header', 'footer', 'sidebar', 'content', 'main'];

    function getMeaningfulClasses(el) {
        if (!el.className || typeof el.className !== 'string') return [];
        return el.className.trim().split(/\s+/).filter(c =>
            c && !FRAMEWORK_CLASS_RE.test(c) && c.length > 1
        );
    }

    function classRelevanceScore(cls, el) {
        // 包含元素文本内容的 class 更有区分度
        const text = (el.textContent || '').toLowerCase();
        const lowerCls = cls.toLowerCase();
        let score = 0;
        if (text && lowerCls.includes(text.substring(0, 10))) score += 2;
        for (const kw of ROLE_KEYWORDS) {
            if (lowerCls.includes(kw)) score += 1;
        }
        // 更长的 class 名通常更具体
        if (cls.length > 8) score += 1;
        return score;
    }

    // CSS.escape() 只适用于标识符 (id, class 名)
    // 属性值在引号内是字面字符串, 只需转义双引号和反斜杠
    function escapeAttrValue(val) {
        return val.replace(/\\/g, '\\\\').replace(/"/g, '\\\"');
    }

    function computeSelectorCandidates(el) {
        const candidates = [];
        const tag = el.tagName.toLowerCase();

        // 1. #id — 如果有 id, 始终排在第一位 (100% 唯一)
        if (el.id) {
            candidates.push('#' + CSS.escape(el.id));
        }

        // 2. tag[href="value"] — <a> 标签带 href (链接通常唯一)
        // 使用 getAttribute('href') 取原始属性值, 而非 el.href (浏览器解析后的绝对URL)
        // querySelectorAll 匹配的是原始属性值, 不是解析后的绝对URL
        const rawHref = el.getAttribute('href');
        if (tag === 'a' && rawHref) {
            candidates.push(tag + '[href="' + escapeAttrValue(rawHref) + '"]');
        }

        // 3. tag[aria-label="value"] — aria-label 属性
        const ariaLabel = el.getAttribute('aria-label');
        if (ariaLabel) {
            candidates.push(tag + '[aria-label="' + escapeAttrValue(ariaLabel) + '"]');
        }

        // 4. tag[name="value"] — name 属性 (input 等表单元素)
        if (el.name) {
            candidates.push(tag + '[name="' + escapeAttrValue(el.name) + '"]');
        }

        // 5. tag[placeholder="value"] — placeholder 属性
        if (el.placeholder) {
            candidates.push(tag + '[placeholder="' + escapeAttrValue(el.placeholder) + '"]');
        }

        // 6 & 7. class 选择器 — 按区分度排序, 最多取 2 个有意义的 class 组合
        const meaningful = getMeaningfulClasses(el);
        if (meaningful.length > 0) {
            // 按相关性评分排序
            const scored = meaningful.map(cls => ({cls, score: classRelevanceScore(cls, el)}));
            scored.sort((a, b) => b.score - a.score);
            const ranked = scored.map(s => s.cls);

            // 双 class 组合 (tag.class1.class2)
            if (ranked.length >= 2) {
                candidates.push(tag + '.' + CSS.escape(ranked[0]) + '.' + CSS.escape(ranked[1]));
            }
            // 单 class (tag.class1)
            candidates.push(tag + '.' + CSS.escape(ranked[0]));
        }

        // 8. tag:nth-child(path) — nth-of-type 路径兜底 (最多 4 层)
        const path = [];
        let current = el;
        let depth = 0;
        while (current && current !== document.body && depth < 4) {
            let seg = current.tagName.toLowerCase();
            // 附加第一个有意义的 class
            const cls = getMeaningfulClasses(current);
            if (cls.length > 0) seg += '.' + CSS.escape(cls[0]);
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
        const nthSelector = path.join(' > ');
        // 避免重复: 如果 nth 路径和已有候选相同则跳过
        if (nthSelector && !candidates.includes(nthSelector)) {
            candidates.push(nthSelector);
        }

        return candidates;
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
        const selector_candidates = computeSelectorCandidates(el);

        results.push({
            tag: el.tagName.toLowerCase(),
            selector_candidates: selector_candidates,
            text: text,
            id: el.id || '',
            className: (el.className && typeof el.className === 'string')
                ? el.className.trim().split(/\s+/).slice(0, 5).join(' ') : '',
            name_attr: el.name || '',
            type: el.type || '',
            href: el.getAttribute('href') || (el.href ? el.href.substring(0, 120) : ''),
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


def _normalize_ws(s):
    """归一化空白: 去除所有空格/换行/tab，用于比较 A11Y name 和 DOM text。

    Accessibility Tree 的 name 经常在数字前插入空格 (如 "项目 0"),
    而 DOM text 的数字紧贴文字 (如 "项目0").
    去除所有空格后比较可消除这类差异。
    """
    return re.sub(r"\s+", "", s) if s else ""


def _match_a11y_to_dom(a11y_nodes, dom_elements):
    """将 Accessibility Tree 交互节点与 DOM 元素交叉匹配。

    匹配策略:
    1. 精确匹配: role 映射到 tag, name 完全等于 text (或 aria_label)
    2. 子串匹配: name 包含在 text 中, 或 text 包含在 name 中
    3. 宽松匹配: role 映射到 tag, 没有文字匹配但 tag 相同

    返回: [{a11y_role, a11y_name, dom_tag, dom_selector, dom_selector_candidates,
            dom_text, match_quality, ...}, ...]
    """
    mappings = []
    used_dom_indices = set()

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
            a11y_norm = _normalize_ws(a11y_name)
            if a11y_name and dom.get("aria_label") and a11y_norm == _normalize_ws(dom["aria_label"]):
                quality = 3
            elif a11y_name and dom.get("text") and a11y_norm == _normalize_ws(dom["text"]):
                quality = 3
            elif a11y_name and dom.get("placeholder") and a11y_norm == _normalize_ws(dom["placeholder"]):
                quality = 3
            elif a11y_name and dom.get("name_attr") and a11y_norm == _normalize_ws(dom["name_attr"]):
                quality = 2
            elif a11y_name and dom.get("id") and a11y_norm == _normalize_ws(dom["id"]):
                quality = 2
            elif a11y_name and dom.get("text") and a11y_norm in _normalize_ws(dom["text"]):
                quality = 1
            elif a11y_name and dom.get("text") and _normalize_ws(dom["text"]) in a11y_norm and len(dom["text"]) > 2:
                quality = 1
            elif not a11y_name and dom["tag"] == "input" and dom.get("type") in ("text", "search", ""):
                quality = 1

            if quality > best_quality:
                best_quality = quality
                best_match_idx = i

        if best_match_idx is not None and best_quality > 0:
            dom = dom_elements[best_match_idx]
            used_dom_indices.add(best_match_idx)
            candidates = dom.get("selector_candidates", [])
            primary = candidates[0] if candidates else ""
            mappings.append({
                "a11y_role": a11y["role"],
                "a11y_name": a11y["name"],
                "a11y_nodeId": a11y["nodeId"],
                "dom_tag": dom["tag"],
                "dom_selector": primary,
                "dom_selector_candidates": candidates,
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
                "dom_selector_candidates": [],
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

    for i, dom in enumerate(dom_elements):
        if i not in used_dom_indices:
            candidates = dom.get("selector_candidates", [])
            primary = candidates[0] if candidates else ""
            mappings.append({
                "a11y_role": "",
                "a11y_name": "",
                "a11y_nodeId": "",
                "dom_tag": dom["tag"],
                "dom_selector": primary,
                "dom_selector_candidates": candidates,
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


def discover(cli, config, url=None):
    """交互式探索目标页面, 输出所有可交互元素, 帮助用户确定 CSS 选择器"""
    target_url = url or config["TARGET_URL"]
    if not target_url:
        print("目标网址未指定, 请通过 --url 参数传入或在 config.yaml 中填写 TARGET_URL")
        return

    print("\n" + "=" * 60)
    print("  Discovery 模式 — 分析页面结构")
    print("=" * 60 + "\n")

    cli.navigate(target_url)
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
                candidates = el.get('selector_candidates', [])
                primary = candidates[0] if candidates else "(无选择器)"
                print("  [%d] <%s>  ★ %s" % (i, el.get('tag'), primary))
                if len(candidates) > 1:
                    for alt in candidates[1:]:
                        print("      ○ %s" % alt)
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
            elements_file = os.path.join(config["OUTPUT_DIR"], "discovery_elements.json")
            with open(elements_file, "w", encoding="utf-8") as f:
                json.dump(elements, f, ensure_ascii=False, indent=2)
            print("  DOM 元素 JSON 已保存: %s" % elements_file)
        else:
            print("  JS 提取结果:", raw[:500])
    except json.JSONDecodeError:
        print("  JS 提取结果 (原始):", result[:500])

    # ── Section 3: Accessibility → CSS 选择器映射表 ──
    print("\n3. Accessibility → CSS 选择器映射表:")
    print("-" * 40)

    mappings = []
    if a11y_nodes and dom_elements:
        mappings = _match_a11y_to_dom(a11y_nodes, dom_elements)

        matched_count = sum(1 for m in mappings if m["matched"])
        total_a11y = len(a11y_nodes)

        # 验证所有候选选择器的唯一性 (批量)
        all_candidates = []
        for m in mappings:
            for sel in m.get("dom_selector_candidates", []):
                if sel and sel not in all_candidates:
                    all_candidates.append(sel)

        selector_counts = {}
        if all_candidates:
            verify_js = VERIFY_SELECTORS_JS % json.dumps(all_candidates)
            try:
                verify_result = cli.evaluate(verify_js)
                raw_v = _strip_cli_hint(verify_result.strip())
                if raw_v.startswith('"') and raw_v.endswith('"'):
                    raw_v = json.loads(raw_v)
                selector_counts = json.loads(raw_v) if isinstance(raw_v, str) else raw_v
            except (json.JSONDecodeError, RuntimeError):
                selector_counts = {}

        # 为每个映射的候选选择器标注唯一性
        for m in mappings:
            annotated = []
            for sel in m.get("dom_selector_candidates", []):
                cnt = selector_counts.get(sel, -1)
                annotated.append({
                    "selector": sel,
                    "unique": cnt == 1,
                    "match_count": cnt,
                })
            m["dom_selector_candidates"] = annotated

        # 输出映射表 (★ 最佳 + ○ 替代) — 同时收集文本用于保存
        table_lines = []
        table_lines.append("  %-20s  选择器候选列表" % "Accessibility节点")
        table_lines.append("")
        for m in mappings:
            a11y_label = "[%s] %s" % (m["a11y_role"], m["a11y_name"][:25] if m["a11y_name"] else "(无名称)")
            candidates = m.get("dom_selector_candidates", [])
            if m["matched"] or m["dom_selector"]:
                extras = []
                if m["dom_id"]:
                    extras.append("id=" + m["dom_id"])
                if m["dom_type"]:
                    extras.append("type=" + m["dom_type"])
                if m["dom_placeholder"]:
                    extras.append("placeholder=" + m["dom_placeholder"][:30])
                if m["dom_href"]:
                    extras.append("href=" + m["dom_href"][:40])
                extra_str = "  " + ", ".join(extras) if extras else ""

                if m["matched"]:
                    line = "  %s" % a11y_label
                else:
                    line = "  %-20s  (仅DOM)" % "(未在Tree中)"
                table_lines.append(line)

                if candidates:
                    best = candidates[0]
                    best_tag = "★" if best.get("unique") else "○"
                    uniq_mark = "(唯一 ✓)" if best.get("unique") else "(匹配%d个)" % best.get("match_count", -1)
                    table_lines.append("    %s %s   %s" % (best_tag, best["selector"], uniq_mark))
                    for alt in candidates[1:]:
                        alt_tag = "★" if alt.get("unique") else "○"
                        alt_mark = "(唯一 ✓)" if alt.get("unique") else "(匹配%d个)" % alt.get("match_count", -1)
                        table_lines.append("    %s %s   %s" % (alt_tag, alt["selector"], alt_mark))
                if extra_str:
                    table_lines.append("    %s" % extra_str)
            else:
                table_lines.append("  %s  (未找到对应的 HTML 元素)" % a11y_label)

        table_lines.append("")
        table_lines.append("  匹配统计: %d/%d Accessibility节点已匹配到DOM元素" % (matched_count, total_a11y))

        # 打印映射表到终端
        for line in table_lines:
            print(line)

        # 保存映射表 JSON
        mapping_file = os.path.join(config["OUTPUT_DIR"], "discovery_mapping.json")
        with open(mapping_file, "w", encoding="utf-8") as f:
            json.dump(mappings, f, ensure_ascii=False, indent=2)
        print("  映射表 JSON 已保存: %s" % mapping_file)

        # 保存映射表可读文本
        mapping_txt_file = os.path.join(config["OUTPUT_DIR"], "discovery_mapping_table.txt")
        with open(mapping_txt_file, "w", encoding="utf-8") as f:
            f.write("Accessibility → CSS 选择器映射表\n")
            f.write("=" * 60 + "\n")
            for line in table_lines:
                f.write(line + "\n")
        print("  映射表文本已保存: %s" % mapping_txt_file)

        # 非唯一选择器汇总
        non_unique_primary = [m for m in mappings if m["dom_selector"] and m["dom_selector_candidates"] and not m["dom_selector_candidates"][0].get("unique", False)]
        if non_unique_primary:
            print("\n  ⚠ 以下首选选择器非唯一 (建议使用替代选择器或添加限定):")
            for m in non_unique_primary:
                best = m["dom_selector_candidates"][0]
                print("    %s → 匹配 %d 个元素" % (best["selector"], best["match_count"]))
        else:
            all_unique = all(
                m["dom_selector_candidates"][0].get("unique", False)
                for m in mappings if m["dom_selector_candidates"]
            )
            if all_unique:
                print("  ✓ 所有首选选择器均唯一匹配")

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
    if mappings:
        for m in mappings:
            if m["matched"] and m["dom_selector"]:
                if m["a11y_role"] in ("textbox", "searchbox", "combobox"):
                    key_selectors.append(("输入框", m["dom_selector"], m["a11y_name"], m.get("dom_selector_candidates", [])))
                elif m["a11y_role"] == "button" and any(
                    kw in (m["a11y_name"] or "").lower()
                    for kw in ["搜索", "search", "提交", "submit", "查询", "login", "登录"]
                ):
                    key_selectors.append(("操作按钮", m["dom_selector"], m["a11y_name"], m.get("dom_selector_candidates", [])))

    if key_selectors:
        print("  关键元素提示:")
        for label, sel, name, candidates in key_selectors[:6]:
            print("    %s: ★ selector=\"%s\" (Accessibility名称: \"%s\")" % (label, sel, name))
            if candidates:
                unique_alts = [c for c in candidates if c.get("unique") and c["selector"] != sel]
                if unique_alts:
                    print("      替代选择器: %s" % ", ".join(c["selector"] for c in unique_alts[:3]))
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
    time.sleep(3)
    cli.screenshot(screenshot_path)
    print("5. 页面截图已保存: %s" % screenshot_path)
    print("   请查看截图确认页面结构\n")