"""
Discovery 模式 — 分析页面可交互元素, 帮助用户编写 STEPS 配置

输出 3 个部分:
  1. 可交互元素列表 (带 ★/○ 唯一性标记的选择器候选)
  2. STEPS 配置建议 (基于关键元素的 match/selector 提示)
  3. 页面截图

同时保存 JSON 数据到 OUTPUT_DIR, 方便离线查阅。

元素定位的更多方法, 请参见 docs/devtools-guide.md。
"""

import json
import os
import re
import time
import logging

log = logging.getLogger("chrome_auto_fetch")


def _strip_cli_hint(text):
    """chrome-devtools evaluate 输出可能包含 [HINT] 行, 需剥离后再解析 JSON"""
    lines = text.split('\n')
    clean_lines = [l for l in lines if not l.strip().startswith('[HINT')]
    return '\n'.join(clean_lines).strip()


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
        const text = (el.textContent || '').toLowerCase();
        const lowerCls = cls.toLowerCase();
        let score = 0;
        if (text && lowerCls.includes(text.substring(0, 10))) score += 2;
        for (const kw of ROLE_KEYWORDS) {
            if (lowerCls.includes(kw)) score += 1;
        }
        if (cls.length > 8) score += 1;
        return score;
    }

    function escapeAttrValue(val) {
        return val.replace(/\\/g, '\\\\').replace(/"/g, '\\\"');
    }

    function computeSelectorCandidates(el) {
        const candidates = [];
        const tag = el.tagName.toLowerCase();

        // 1. #id
        if (el.id) {
            candidates.push('#' + CSS.escape(el.id));
        }

        // 2. tag[href="value"]
        const rawHref = el.getAttribute('href');
        if (tag === 'a' && rawHref) {
            candidates.push(tag + '[href="' + escapeAttrValue(rawHref) + '"]');
        }

        // 3. tag[aria-label="value"]
        const ariaLabel = el.getAttribute('aria-label');
        if (ariaLabel) {
            candidates.push(tag + '[aria-label="' + escapeAttrValue(ariaLabel) + '"]');
        }

        // 4. tag[name="value"]
        if (el.name) {
            candidates.push(tag + '[name="' + escapeAttrValue(el.name) + '"]');
        }

        // 5. tag[placeholder="value"]
        if (el.placeholder) {
            candidates.push(tag + '[placeholder="' + escapeAttrValue(el.placeholder) + '"]');
        }

        // 6 & 7. class 选择器 — 按区分度排序
        const meaningful = getMeaningfulClasses(el);
        if (meaningful.length > 0) {
            const scored = meaningful.map(cls => ({cls, score: classRelevanceScore(cls, el)}));
            scored.sort((a, b) => b.score - a.score);
            const ranked = scored.map(s => s.cls);

            if (ranked.length >= 2) {
                candidates.push(tag + '.' + CSS.escape(ranked[0]) + '.' + CSS.escape(ranked[1]));
            }
            candidates.push(tag + '.' + CSS.escape(ranked[0]));
        }

        // 8. nth-of-type 路径兜底 (最多 4 层)
        const path = [];
        let current = el;
        let depth = 0;
        while (current && current !== document.body && depth < 4) {
            let seg = current.tagName.toLowerCase();
            const cls = getMeaningfulClasses(current);
            if (cls.length > 0) seg += '.' + CSS.escape(cls[0]);
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
            results[sel] = -1;
        }
    }
    return JSON.stringify(results);
})()
"""


def _verify_selectors(cli, selectors):
    """批量验证选择器唯一性, 返回 {selector: match_count}"""
    if not selectors:
        return {}
    verify_js = VERIFY_SELECTORS_JS % json.dumps(selectors)
    try:
        verify_result = cli.evaluate(verify_js)
        raw_v = _strip_cli_hint(verify_result.strip())
        if raw_v.startswith('"') and raw_v.endswith('"'):
            raw_v = json.loads(raw_v)
        return json.loads(raw_v) if isinstance(raw_v, str) else raw_v
    except (json.JSONDecodeError, RuntimeError):
        return {}


def discover(cli, config, url=None):
    """探索目标页面的可交互元素, 帮助用户编写 STEPS 配置"""
    target_url = url or config["TARGET_URL"]
    if not target_url:
        print("目标网址未指定, 请通过 --url 参数传入或在 config.yaml 中填写 TARGET_URL")
        return

    print("\n" + "=" * 60)
    print("  Discovery 模式 — 分析页面可交互元素")
    print("=" * 60 + "\n")

    cli.navigate(target_url)
    time.sleep(config["STEP_DELAY"])

    os.makedirs(config["OUTPUT_DIR"], exist_ok=True)

    # ── Section 1: 可交互元素 (增强版 JS 提取 + 选择器唯一性验证) ──
    print("1. 可交互元素 (input/select/button/textarea/a):")
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

            # 批量验证所有候选选择器的唯一性
            all_candidates = []
            for el in elements:
                for sel in el.get("selector_candidates", []):
                    if sel and sel not in all_candidates:
                        all_candidates.append(sel)
            selector_counts = _verify_selectors(cli, all_candidates)

            # 标注唯一性并输出
            for i, el in enumerate(elements):
                candidates = el.get('selector_candidates', [])
                if not candidates:
                    print("  [%d] <%s>  (无选择器候选)" % (i, el.get('tag')))
                    continue

                primary = candidates[0]
                primary_count = selector_counts.get(primary, -1)
                primary_mark = "★" if primary_count == 1 else "○"
                primary_uniq = "(唯一 ✓)" if primary_count == 1 else "(匹配%d个)" % primary_count
                print("  [%d] <%s>  %s %s   %s" % (i, el.get('tag'), primary_mark, primary, primary_uniq))

                for alt in candidates[1:]:
                    alt_count = selector_counts.get(alt, -1)
                    alt_mark = "★" if alt_count == 1 else "○"
                    alt_uniq = "(唯一 ✓)" if alt_count == 1 else "(匹配%d个)" % alt_count
                    print("      %s %s   %s" % (alt_mark, alt, alt_uniq))

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

            # 非唯一选择器汇总
            non_unique = []
            for el in elements:
                candidates = el.get('selector_candidates', [])
                if candidates:
                    primary = candidates[0]
                    count = selector_counts.get(primary, -1)
                    if count != 1:
                        non_unique.append((primary, count))
            if non_unique:
                print("  ⚠ 以下首选选择器非唯一:")
                for sel, cnt in non_unique[:10]:
                    print("    %s → 匹配 %d 个元素" % (sel, cnt))

            # 保存 JSON
            # 将 selector_counts 注入到每个元素的 candidates 中
            for el in elements:
                annotated = []
                for sel in el.get("selector_candidates", []):
                    cnt = selector_counts.get(sel, -1)
                    annotated.append({
                        "selector": sel,
                        "unique": cnt == 1,
                        "match_count": cnt,
                    })
                el["selector_candidates_verified"] = annotated

            elements_file = os.path.join(config["OUTPUT_DIR"], "discovery_elements.json")
            with open(elements_file, "w", encoding="utf-8") as f:
                json.dump(elements, f, ensure_ascii=False, indent=2)
            print("  元素数据已保存: %s" % elements_file)

        else:
            print("  JS 提取结果:", raw[:500])
    except json.JSONDecodeError:
        print("  JS 提取结果 (原始):", result[:500])

    # ── Section 2: STEPS 配置建议 ──
    print("\n2. STEPS 配置建议:")
    print("-" * 40)

    if dom_elements:
        # 从元素中提取关键元素 (输入框 + 搜索按钮)
        key_inputs = []
        key_buttons = []
        for el in dom_elements:
            candidates = el.get('selector_candidates', [])
            if not candidates:
                continue
            primary = candidates[0]
            primary_count = selector_counts.get(primary, -1)

            # 输入框
            if el.get('tag') in ('input', 'textarea', 'select'):
                el_type = el.get('type', '')
                if el_type in ('text', 'search', '', 'textarea') or el.get('tag') == 'select':
                    best = primary if primary_count == 1 else None
                    key_inputs.append({
                        "selector": best or primary,
                        "unique": primary_count == 1,
                        "text": el.get('text', ''),
                        "placeholder": el.get('placeholder', ''),
                        "name": el.get('name_attr', ''),
                        "aria_label": el.get('aria_label', ''),
                    })

            # 搜索/提交按钮
            if el.get('tag') == 'button' or el.get('role') == 'button':
                btn_text = el.get('text', '').lower()
                if any(kw in btn_text for kw in ['搜索', 'search', '提交', 'submit', '查询', 'login', '登录', '确定', 'confirm']):
                    best = primary if primary_count == 1 else None
                    key_buttons.append({
                        "selector": best or primary,
                        "unique": primary_count == 1,
                        "text": el.get('text', ''),
                    })

        if key_inputs:
            print("  输入框:")
            for inp in key_inputs[:5]:
                uniq = "★" if inp["unique"] else "○"
                desc = inp["placeholder"] or inp["aria_label"] or inp["name"] or inp["text"]
                print("    %s selector=\"%s\"  (%s)" % (uniq, inp["selector"], desc[:40]))
            print()

        if key_buttons:
            print("  操作按钮:")
            for btn in key_buttons[:3]:
                uniq = "★" if btn["unique"] else "○"
                print("    %s selector=\"%s\"  (text: %s)" % (uniq, btn["selector"], btn["text"][:30]))
            print()

        # 提供 match 方式提示 (如果有 href/aria-label/name/placeholder)
        print("  可用 match 方式定位的元素:")
        match_suggestions = []
        for el in dom_elements:
            if el.get('href') and el.get('tag') == 'a':
                match_suggestions.append(("href", el['href'][:60], el.get('text', '')[:30]))
            if el.get('aria_label'):
                match_suggestions.append(("aria_label", el['aria_label'][:40], el.get('text', '')[:30]))
            if el.get('name_attr') and el.get('tag') == 'input':
                match_suggestions.append(("name", el['name_attr'], el.get('placeholder', '')[:30]))
            if el.get('placeholder') and el.get('tag') == 'input':
                match_suggestions.append(("placeholder", el['placeholder'][:40], el.get('text', '')[:20]))
        if match_suggestions:
            for match_type, match_val, desc in match_suggestions[:10]:
                print("    match: %s  value: \"%s\"  (%s)" % (match_type, match_val, desc))
        else:
            print("    (无)")
        print()

    print("  STEPS 模板:")
    print("    - action: navigate")
    print("      url: \"%s\"" % target_url)
    print("    - action: fill")
    print("      selector: \"<输入框>\"     # 或: match: placeholder/name + value + content")
    print("      content: \"<搜索内容>\"")
    print("    - action: click")
    print("      selector: \"<搜索按钮>\"    # 或: match: text + value: \"搜索\"")
    print("    - action: wait")
    print("      strategy: element")
    print("      selector: \"<结果区域>\"")
    print("    - action: click")
    print("      selector: \"<结果链接>\"    # 或: match: href + value: \"<链接路径>\"")
    print("    - action: extract")
    print("      strategy: css")
    print("      selector: \"<下载链接>\"")
    print("      save_to: \"download_urls\"")
    print("    - action: save")
    print()
    print("  提示: 使用 Chrome DevTools 元素检查器可以更精确地定位元素")
    print("  详见 docs/devtools-guide.md")
    print()

    # ── Section 3: 页面截图 ──
    screenshot_path = os.path.join(config["OUTPUT_DIR"], "discovery_screenshot.png")
    time.sleep(3)
    cli.screenshot(screenshot_path)
    print("3. 页面截图已保存: %s" % screenshot_path)
    print("   请查看截图确认页面结构\n")