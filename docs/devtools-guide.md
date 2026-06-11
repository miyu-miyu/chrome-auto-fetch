# Chrome DevTools 元素定位指南

chrome-auto-fetch 通过 CSS 选择器或属性匹配定位页面元素。当你需要编写 STEPS 配置时，最快的方法不是运行 discover 模式，而是**直接在 Chrome DevTools 中检查目标元素**。

> **如果你不熟悉 CSS 选择器语法**（什么是 `#id`、`.class`、`[attr='val']`），请先阅读 [选择器入门指南](selector-guide.md)，了解选择器的写法规则后再回来。

---

## 1. 为什么用 DevTools 比 discover 更好

| 方面 | DevTools | discover 模式 |
|---|---|---|
| 定位精度 | 直接看到目标元素的所有属性 | 批量输出所有元素，需要自己找 |
| 选择器质量 | Chrome 自动生成 Copy selector | 基于规则的候选列表，可能不准确 |
| 适用范围 | 任何元素（包括动态生成的） | 只覆盖 `input/select/button/textarea/a[href]` |
| 操作成本 | 右键 → 检查 → 复制，30秒完成 | 运行命令 → 等待 → 在输出中搜索 |
| 学习成本 | 无需学 CSS 选择器语法 | 需要理解候选列表和唯一性标记 |

**建议流程**：先在 DevTools 中定位关键元素（搜索框、按钮、结果链接），再快速编写 STEPS。discover 模式适合需要全面了解页面结构时使用。

---

## 2. 基础操作：右键检查元素

### 2.1 打开 DevTools

在目标网页上：

1. **右键点击** 你要定位的元素（输入框、按钮、链接等）
2. 选择 **"检查"** (Inspect)
3. DevTools 面板打开，自动定位到该元素的 HTML 代码

或者按快捷键：
- macOS: `Cmd + Option + I`
- Windows/Linux: `Ctrl + Shift + I`

### 2.2 读取元素信息

在 DevTools 的 Elements 面板中，选中元素后你会看到：

```html
<!-- 示例：搜索输入框 -->
<input id="golbalSearch" name="query" placeholder="搜索项目" type="text" class="search-input">

<!-- 示例：搜索按钮 -->
<button class="btn btn-primary search-btn" aria-label="搜索">搜索</button>

<!-- 示例：结果链接 -->
<a href="/openharmony/kernel" class="result-link">OpenHarmony内核</a>
```

从 HTML 中你可以直接读取以下信息用于 STEPS 配置：

| HTML 属性 | STEPS 参数 | 示例 |
|---|---|---|
| `id="xxx"` | `selector: "#xxx"` | `selector: "#golbalSearch"` |
| `class="xxx"` | `selector: "tag.xxx"` | `selector: "input.search-input"` |
| `href="/path"` | `match: href` + `value: "/path"` | `match: href, value: "/openharmony/kernel"` |
| `aria-label="xxx"` | `match: aria_label` + `value: "xxx"` | `match: aria_label, value: "搜索"` |
| `name="xxx"` | `match: name` + `value: "xxx"` | `match: name, value: "query"` |
| `placeholder="xxx"` | `match: placeholder` + `value: "xxx"` | `match: placeholder, value: "搜索项目"` |
| 元素文本内容 | `match: text` + `value: "xxx"` | `match: text, value: "搜索"` |

---

## 3. 快速获取选择器：Copy selector

Chrome DevTools 可以自动生成 CSS 选择器，省去手动编写的时间。

### 3.1 操作步骤

1. 在 DevTools Elements 面板中**右键点击**目标元素的 HTML 代码
2. 选择 **Copy → Copy selector**
3. 粘贴到 STEPS 配置中

### 3.2 生成的选择器格式

Chrome 生成的选择器通常是 `#id` 或层级路径：

```
#golbalSearch                              ← 有 id 时，直接用 id
#search-form > div:nth-child(2) > input    ← 无 id 时，生成层级路径
```

- **有 id 的元素**：生成的选择器就是 `#id`，稳定且唯一，直接用
- **无 id 的元素**：生成的是 `nth-child` 层级路径，如 `div > button:nth-child(3)`，**页面结构变化时会失效**

### 3.3 选择器稳定性建议

| 选择器类型 | 稳定性 | 建议 |
|---|---|---|
| `#id` | 最稳定 | ✅ 直接用 |
| `[href="..."]` | 稳定 | ✅ 用 `match: href` |
| `[aria-label="..."]` | 稳定 | ✅ 用 `match: aria_label` |
| `[name="..."]` | 稳定 | ✅ 用 `match: name` |
| `[placeholder="..."]` | 稳定 | ✅ 用 `match: placeholder` |
| `.class-name` | 中等 | ⚠ 检查是否唯一 |
| `nth-child` 路径 | 最不稳定 | ❌ 仅作为兜底 |

---

## 4. 进阶：读取自定义属性

有些元素的关键信息不在标准属性中，而是在自定义属性（如 `ng-click`、`data-*` 等）。

### 4.1 AngularJS / Vue / React 属性

```html
<!-- AngularJS -->
<td ng-click="downloadReleaseFolder(item, 'solution', 'log')" ng-show="item.folderMap.log=='unload'">
  <span class="folderStyle">log</span>
</td>

<!-- Vue -->
<div data-v-abc123 class="card" @click="handleClick">

<!-- React -->
<button data-testid="submit-btn" class="btn">
```

从这些元素中提取定位信息：

| 属性 | 用法 | STEPS 示例 |
|---|---|---|
| `ng-click="..."` | CSS 属性选择器 | `selector: "td[ng-click*='log']"` |
| `data-testid="..."` | CSS 属性选择器 | `selector: "[data-testid='submit-btn']"` |
| `data-v-xxx` | ❌ 不推荐 | 框架生成，不稳定 |
| 子元素文本 | `match: text` | `match: text, value: "log"` |

### 4.2 ng-click 属性选择器写法

AngularJS 的 `ng-click` 是很好的定位属性：

```yaml
# 精确匹配 ng-click 值
- action: click
  selector: "td[ng-click='downloadReleaseFolder(item, solution, log)']"

# 部分匹配（更灵活，值中包含 log）
- action: click
  selector: "td[ng-click*='log']"

# 定位子元素 span
- action: click
  selector: "td[ng-click*='log'] span.folderStyle"
```

---

## 5. 验证选择器唯一性

复制选择器后，建议在 DevTools Console 中验证它是否唯一匹配目标元素。

### 5.1 操作步骤

1. 打开 DevTools Console 面板（点击 Console 标签）
2. 输入：`document.querySelectorAll('你的选择器').length`
3. 回车执行

```
> document.querySelectorAll('#golbalSearch').length
1                                    ← 唯一 ✓，可以安全使用

> document.querySelectorAll('a.result-link').length
5                                    ← 非唯一 ✗，需要更具体的选择器

> document.querySelectorAll('td[ng-click*="log"]').length
1                                    ← 唯一 ✓
```

### 5.2 如果不唯一

选择器匹配多个元素时，需要加限定条件：

```yaml
# 方案1: 更具体的选择器（加上父元素限定）
selector: ".search-panel input.search-input"

# 方案2: 使用 match 替代（属性值通常唯一）
match: placeholder
value: "搜索项目"

# 方案3: 指定 index（第几个匹配元素）
selector: "a.result-link"
index: 2                    # 第2个匹配元素

# 方案4: 用 href 精确匹配链接
match: href
value: "/openharmony/kernel"
```

---

## 6. 定位表格中的元素

表格是常见的难点场景。DevTools 中检查表格单元格：

```html
<table>
  <tbody>
    <tr>
      <td ng-click="downloadReleaseFolder(item, 'solution', 'log')">
        <span class="folderStyle">log</span>
      </td>
    </tr>
  </tbody>
</table>
```

### 6.1 定位策略

```yaml
# 定位单元格 td（通过 ng-click 属性）
- action: click
  selector: "td[ng-click*='log']"

# 定位单元格内的 span（最精确）
- action: click
  selector: "td[ng-click*='log'] span.folderStyle"

# 定位第 N 行的单元格（组合 nth-of-type）
- action: click
  selector: "tbody tr:nth-of-type(2) td[ng-click*='log']"

# 如果只有文本可区分（用 match: text）
- action: click
  match: text
  value: "log"
  tag: "span"
```

更多表格定位技巧见 [选择器入门指南](selector-guide.md) 的"问题8: 表格定位"。

---

## 7. 定位动态元素

有些元素在操作后才出现（如弹窗、下拉菜单），DevTools 中可能看不到。

### 7.1 方法：先触发，再检查

1. 在页面上**手动点击**触发元素（让弹窗/下拉菜单出现）
2. 右键检查出现的弹窗元素
3. 复制选择器

### 7.2 方法：在 Console 中临时显示

```javascript
// 临时让隐藏元素可见，方便检查
document.querySelectorAll('[style*="display: none"]').forEach(el => el.style.display = 'block')

// 检查完之后恢复
document.querySelectorAll('[style*="display: block"]').forEach(el => {
  if (el.originalDisplay) el.style.display = el.originalDisplay
})
```

---

## 8. 定位嵌套深层元素

当目标元素在多层相同属性的 div 中，只有最上层 div 属性不同：

```html
<div class="project-card">               ← 最上层，属性不同
  <div class="content">                  ← 中间层，属性相同
    <div class="content">                ← 中间层，属性相同
      <span class="folderStyle">log</span> ← 目标元素
    </div>
  </div>
</div>
```

写法：从最上层开始往下写路径：

```yaml
selector: "div.project-card span.folderStyle"
```

或者只关注目标元素本身和最近的有区分度的父元素：

```yaml
selector: ".project-card .folderStyle"
```

---

## 9. 常见场景速查表

| 场景 | 推荐方法 | STEPS 配置 |
|---|---|---|
| 搜索输入框 | `selector: "#id"` 或 `match: placeholder` | `selector: "#golbalSearch"` 或 `match: placeholder, value: "搜索项目", content: "OpenHarmony"` |
| 搜索按钮 | `selector: "#id"` 或 `match: text` | `selector: ".search-btn"` 或 `match: text, value: "搜索"` |
| 结果列表中的链接 | `match: href` | `match: href, value: "/openharmony/kernel"` |
| 下载按钮 | `match: text` 或 `selector` | `match: text, value: "下载"` 或 `selector: ".download-btn"` |
| 表格单元格 | `selector` + 属性 | `selector: "td[ng-click*='log']"` |
| 弹窗中的按钮 | 先触发弹窗再检查 | `selector: ".modal .confirm-btn"` |
| 下拉菜单选项 | 先打开菜单再检查 | `selector: ".dropdown li:nth-of-type(3)"` 或 `match: text, value: "选项名"` |

---

## 10. Console 辅助命令

以下命令粘贴到 Chrome DevTools Console 中执行，帮助你快速获取元素信息、编写 STEPS 配置、验证自动化点击是否命中预期目标。

### 10.1 `inspectEl` — 点击任意元素，打印 STEPS 可用信息

在 Console 中粘贴以下代码，之后**点击页面上的任意元素**，Console 会自动打印该元素可用于 STEPS 编写的所有属性：

```javascript
// 安装: 粘贴到 Console 执行一次，之后点击页面元素即可
window.inspectEl = function(el) {
  const tag = el.tagName.toLowerCase();
  const id = el.id;
  const href = el.getAttribute('href');
  const name = el.name || el.getAttribute('name');
  const placeholder = el.placeholder || el.getAttribute('placeholder');
  const ariaLabel = el.getAttribute('aria-label');
  const text = el.textContent.trim().substring(0, 60);
  const ngClick = el.getAttribute('ng-click');
  const dataTestId = el.getAttribute('data-testid');
  const className = (typeof el.className === 'string') ? el.className.trim() : '';

  console.group('📋 STEPS 可用信息 — <%s>', tag + (id ? '#' + id : ''));
  
  // selector 建议
  const suggestions = [];
  if (id) suggestions.push({ type: 'selector', value: '#' + id, note: '✅ id 唯一' });
  if (href) suggestions.push({ type: 'match: href', value: href, note: '链接选择' });
  if (ariaLabel) suggestions.push({ type: 'match: aria_label', value: ariaLabel, note: '无障碍标签' });
  if (name) suggestions.push({ type: 'match: name', value: name, note: '表单 name' });
  if (placeholder) suggestions.push({ type: 'match: placeholder', value: placeholder, note: '占位文本' });
  if (ngClick) suggestions.push({ type: 'selector', value: tag + '[ng-click*="' + ngClick.substring(0, 30) + '"]', note: 'ng-click 属性' });
  if (dataTestId) suggestions.push({ type: 'selector', value: '[data-testid="' + dataTestId + '"]', note: '测试 ID' });
  if (text && text.length < 20) suggestions.push({ type: 'match: text', value: text, note: '文本匹配' });
  
  // 有意义的 class
  const meaningfulClasses = (className || '').split(/\s+/).filter(c => 
    c && c.length > 1 && !/^(devui|ng-|cdk|mat-|Mui)/i.test(c)
  );
  if (meaningfulClasses.length > 0) {
    suggestions.push({ type: 'selector', value: tag + '.' + meaningfulClasses[0], note: 'class 选择器 (需验证唯一性)' });
  }

  console.log('🔧 定位建议:');
  for (const s of suggestions) {
    console.log('  %s: %s  (%s)', s.type, s.value, s.note);
  }
  
  // 唯一性验证
  console.log('\n✅ 唯一性验证:');
  for (const s of suggestions.filter(s => s.type === 'selector')) {
    const count = document.querySelectorAll(s.value).length;
    console.log('  %s → 匹配 %d 个元素 %s', s.value, count, count === 1 ? '✅唯一' : '❌非唯一');
  }

  // fill 命令提示 (如果是输入框)
  if (tag === 'input' || tag === 'textarea' || tag === 'select') {
    console.log('\n📝 fill 步骤:');
    if (id) console.log('  selector: "#%s"', id);
    else if (name) console.log('  match: name\n  value: "%s"', name);
    else if (placeholder) console.log('  match: placeholder\n  value: "%s"', placeholder);
    console.log('  content: "<你要填入的值>"');
  }

  // click 命令提示
  console.log('\n🖱️ click 步骤:');
  if (id) console.log('  selector: "#%s"', id);
  else if (suggestions.length > 0) console.log('  %s', suggestions[0].type + ': ' + suggestions[0].value);

  console.log('\n📄 原始属性:');
  console.log('  tag=%s, id=%s, href=%s, name=%s', tag, id || '', href || '', name || '');
  console.log('  placeholder=%s, aria-label=%s, text="%s"', placeholder || '', ariaLabel || '', text);
  if (ngClick) console.log('  ng-click=%s', ngClick);
  if (dataTestId) console.log('  data-testid=%s', dataTestId);
  if (meaningfulClasses.length) console.log('  class=%s', meaningfulClasses.join(', '));

  console.groupEnd();
  return el;
};

// 自动监听点击: 安装后点击页面任何元素都会触发打印
document.addEventListener('click', function(e) {
  window.inspectEl(e.target);
}, true);
console.log('✅ inspectEl 已安装 — 点击页面元素即可查看 STEPS 信息');
console.log('💡 也可手动调用: inspectEl(document.querySelector("选择器"))');
```

**使用方式：**

1. 粘贴到 Console 执行
2. 点击页面上的输入框、按钮、链接等元素
3. Console 自动打印该元素的 `selector`/`match` 建议 + 唯一性验证 + STEPS 步骤模板
4. 直接复制建议到 config.yaml

**手动调用方式（不依赖点击）：**

```javascript
// 查看指定选择器的元素信息
inspectEl(document.querySelector('#golbalSearch'))

// 查看 match:text 找到的元素
inspectEl(document.querySelectorAll('a').find(a => a.textContent.includes('OpenHarmony')))
```

**取消监听：**

```javascript
// 如果不想每次点击都触发，可以移除监听
document.removeEventListener('click', window._inspectElHandler, true);
```

### 10.2 `verifyClick` — 验证 CDP 点击是否命中预期目标

自动化程序通过 CDP 鼠标事件点击时，可能因为遮挡或坐标偏差而点击到了错误元素。`verifyClick` 命令帮你验证：**给定选择器，CDP 会实际点击到哪个元素？**

```javascript
// 安装: 粘贴到 Console 执行一次
window.verifyClick = function(selector) {
  const el = document.querySelector(selector);
  if (!el) {
    console.error('❌ 未找到元素: %s', selector);
    return null;
  }

  // 1. scrollIntoView 前的状态
  const rectBefore = el.getBoundingClientRect();
  console.log('📍 元素位置 (scrollIntoView 前):');
  console.log('  x=%d, y=%d, width=%d, height=%d', rectBefore.x, rectBefore.y, rectBefore.width, rectBefore.height);
  console.log('  视口内: %s', rectBefore.top >= 0 && rectBefore.bottom <= window.innerHeight ? '✅是' : '❌否');

  // 2. 执行 scrollIntoView({block:'center'})
  el.scrollIntoView({block: 'center'});
  // 等待滚动完成后重新获取位置
  setTimeout(() => {}, 100);
  const rectAfter = el.getBoundingClientRect();
  const centerX = Math.round(rectAfter.x + rectAfter.width / 2);
  const centerY = Math.round(rectAfter.y + rectAfter.height / 2);

  console.log('\n📍 元素位置 (scrollIntoView 后):');
  console.log('  x=%d, y=%d, width=%d, height=%d', rectAfter.x, rectAfter.y, rectAfter.width, rectAfter.height);
  console.log('  中心点: (%d, %d)', centerX, centerY);

  // 3. 检查中心点是否被遮挡
  const hitEl = document.elementFromPoint(centerX, centerY);
  const isTarget = hitEl === el || el.contains(hitEl);
  const isOccluded = !isTarget;

  console.log('\n🎯 CDP 点击命中分析:');
  if (isTarget) {
    console.log('  ✅ 点击 (%d, %d) 会命中目标元素 <%s>', centerX, centerY, el.tagName.toLowerCase());
  } else {
    console.log('  ❌ 点击 (%d, %d) 会命中遮挡元素 <%s>', centerX, centerY, hitEl ? hitEl.tagName.toLowerCase() : 'null');
    if (hitEl) {
      const hitRect = hitEl.getBoundingClientRect();
      console.log('     遮挡元素: class="%s", id="%s"', hitEl.className || '', hitEl.id || '');
      console.log('     遮挡元素位置: x=%d, y=%d, height=%d', hitRect.x, hitRect.y, hitRect.height);
      
      // 计算偏移量: 需要向上滚动多少才能避开遮挡
      const offsetNeeded = hitRect.height + 10;
      console.log('     💡 建议偏移: scrollBy(0, -%d) 或 scrollIntoView 后再偏移', offsetNeeded);
      
      // 验证偏移后能否命中
      const offsetY = centerY - offsetNeeded;
      const hitAfterOffset = document.elementFromPoint(centerX, offsetY);
      const isTargetAfterOffset = hitAfterOffset === el || el.contains(hitAfterOffset);
      if (isTargetAfterOffset) {
        console.log('     ✅ 偏移后点击 (%d, %d) 可以命中目标元素', centerX, offsetY);
      } else {
        console.log('     ❌ 偏移后仍然被遮挡，命中 <%s>', hitAfterOffset ? hitAfterOffset.tagName.toLowerCase() : 'null');
      }
    }
  }

  // 4. 检查目标元素的 visibility/display 状态
  const style = window.getComputedStyle(el);
  const display = style.display;
  const visibility = style.visibility;
  const opacity = style.opacity;
  const ngHide = el.getAttribute('ng-hide') || el.classList.contains('ng-hide');
  
  console.log('\n🔍 元素可见性:');
  console.log('  display=%s, visibility=%s, opacity=%s', display, visibility, opacity);
  if (ngHide) console.log('  ⚠ AngularJS ng-hide 状态: 元素可能被隐藏');

  // 5. 检查父元素是否有 ng-hide
  let parent = el.parentElement;
  let depth = 0;
  while (parent && depth < 3) {
    const parentNgHide = parent.getAttribute('ng-hide') || parent.classList.contains('ng-hide');
    const parentStyle = window.getComputedStyle(parent);
    if (parentNgHide || parentStyle.display === 'none') {
      console.log('  ⚠ 第 %d 层父元素 <%s> 有 ng-hide/display:none', depth + 1, parent.tagName.toLowerCase());
    }
    parent = parent.parentElement;
    depth++;
  }

  console.log('\n📋 总结:');
  if (isTarget && display !== 'none' && visibility !== 'hidden') {
    console.log('  ✅ CDP 点击 selector "%s" 可以正确命中目标', selector);
    console.log('  STEPS: selector: "%s"', selector);
  } else if (isOccluded) {
    console.log('  ❌ CDP 点击 selector "%s" 会命中遮挡元素', selector);
    console.log('  💡 方案: 用 evaluate 先 scrollIntoView, 再用 selector 点击');
    console.log('  STEPS:');
    console.log('    - action: evaluate');
    console.log('      expr: "document.querySelector(\'%s\').scrollIntoView({block:\'center\'})"', selector);
    console.log('    - action: click');
    console.log('      selector: "%s"', selector);
  } else if (display === 'none' || visibility === 'hidden') {
    console.log('  ❌ 目标元素不可见 (display=%s, visibility=%s)', display, visibility);
  }

  return { el, hitEl, isTarget, isOccluded, centerX, centerY };
};

console.log('✅ verifyClick 已安装');
console.log('💡 使用: verifyClick("选择器") — 分析 CDP 点击是否命中预期目标');
```

**使用方式：**

```javascript
// 验证一个选择器是否会被 CDP 正确点击
verifyClick("td[ng-click*='log'] span.folderStyle")

// 验证 id 选择器
verifyClick("#golbalSearch")

// 验证 class 选择器
verifyClick(".search-btn")
```

**输出示例：**

```
📍 元素位置 (scrollIntoView 后):
  x=500, y=300, width=60, height=20
  中心点: (530, 310)

🎯 CDP 点击命中分析:
  ❌ 点击 (530, 310) 会命中遮挡元素 <div>
     遮挡元素: class="pageHead", id=""
     遮挡元素位置: x=0, y=0, height=64
     💡 建议偏移: scrollBy(0, -74) 或 scrollIntoView 后再偏移
     ✅ 偏移后点击 (530, 236) 可以命中目标元素

📋 总结:
  ❌ CDP 点击 selector "td[ng-click*='log'] span.folderStyle" 会命中遮挡元素
  💡 方案: 用 evaluate 先 scrollIntoView, 再用 selector 点击
  STEPS:
    - action: evaluate
      expr: "document.querySelector('td[ng-click*='log'] span.folderStyle').scrollIntoView({block:'center'})"
    - action: click
      selector: "td[ng-click*='log'] span.folderStyle"
```

### 10.3 `checkAllClickable` — 批量检查页面可交互元素的点击可靠性

一键检查页面上所有可交互元素是否会被遮挡：

```javascript
// 安装并执行: 粘贴到 Console，自动扫描所有按钮/链接/输入框
window.checkAllClickable = function() {
  const els = document.querySelectorAll('input, select, button, textarea, a[href], [role="button"], [role="link"]');
  const results = [];
  
  for (const el of els) {
    const rect = el.getBoundingClientRect();
    if (rect.width === 0 && rect.height === 0) continue;

    // scrollIntoView 后检查
    el.scrollIntoView({block: 'center'});
    const rectAfter = el.getBoundingClientRect();
    const cx = Math.round(rectAfter.x + rectAfter.width / 2);
    const cy = Math.round(rectAfter.y + rectAfter.height / 2);
    const hitEl = document.elementFromPoint(cx, cy);
    const isTarget = hitEl === el || el.contains(hitEl);

    const tag = el.tagName.toLowerCase();
    const text = el.textContent.trim().substring(0, 30);
    const selector = el.id ? '#' + el.id : 
                     el.getAttribute('href') ? tag + '[href="' + el.getAttribute('href').substring(0, 40) + '"]' :
                     (el.className && typeof el.className === 'string') ? tag + '.' + el.className.trim().split(/\s+/)[0] : tag;
    
    results.push({
      selector: selector,
      tag: tag,
      text: text,
      clickable: isTarget,
      occludedBy: !isTarget ? (hitEl ? hitEl.tagName.toLowerCase() + '.' + (hitEl.className || '').split(/\s+/)[0] : 'null') : null
    });
  }

  // 滚回顶部
  window.scrollTo(0, 0);

  const occluded = results.filter(r => !r.clickable);
  const ok = results.filter(r => r.clickable);

  console.log('🔍 页面可交互元素点击可靠性检查 (%d 个元素)', results.length);
  console.log('  ✅ 可正确点击: %d 个', ok.length);
  console.log('  ❌ 被遮挡: %d 个', occluded.length);
  
  if (occluded.length > 0) {
    console.log('\n❌ 被遮挡的元素:');
    for (const r of occluded) {
      console.log('  <%s> %s  → 被 <%s> 遮挡', r.tag, r.selector, r.occludedBy);
    }
  }

  return results;
};

checkAllClickable();
```

### 10.4 `watchClicks` — 实时监控所有点击事件的命中目标

监控页面上所有点击事件，打印每次点击实际命中的元素，用于对比自动化程序和手动操作的区别：

```javascript
// 安装: 粘贴到 Console，之后每次点击都会打印命中元素
window._watchClicksHandler = function(e) {
  const hitEl = document.elementFromPoint(e.clientX, e.clientY);
  const target = e.target;
  const isMatch = hitEl === target || target.contains(hitEl);
  
  console.log('🖱️ 点击 (%d, %d):', e.clientX, e.clientY);
  console.log('  event.target: <%s%s%s>  text="%s"',
    target.tagName.toLowerCase(),
    target.id ? '#' + target.id : '',
    (target.className && typeof target.className === 'string') ? '.' + target.className.trim().split(/\s+/)[0] : '',
    target.textContent.trim().substring(0, 30)
  );
  console.log('  elementFromPoint: <%s%s%s>',
    hitEl ? hitEl.tagName.toLowerCase() : 'null',
    hitEl && hitEl.id ? '#' + hitEl.id : '',
    hitEl && hitEl.className && typeof hitEl.className === 'string' ? '.' + hitEl.className.trim().split(/\s+/)[0] : ''
  );
  if (!isMatch) {
    console.log('  ⚠ 两者不一致! CDP 会点击到 <%s> 而非 <%s>',
      hitEl ? hitEl.tagName.toLowerCase() : 'null',
      target.tagName.toLowerCase()
    );
  }
};
document.addEventListener('click', window._watchClicksHandler, true);
console.log('✅ watchClicks 已安装 — 每次点击都会打印命中元素分析');
console.log('💡 取消: document.removeEventListener("click", window._watchClicksHandler, true)');
```

**典型使用场景：**

手动点击一个 `<span>` 触发了弹窗，但自动化程序用 `match: text` 点击同一个 `<span>` 时弹窗内容不同。用 `watchClicks` 对比：

- 手动点击 → `event.target: <span>` + `elementFromPoint: <span>` → CDP 真实鼠标事件 ✅
- 自动化 JS `.click()` → 没有经过 CDP → `isTrusted=false` → AngularJS `mouseover` 未触发 ❌

这时你应该用 `selector` 模式（CDP 鼠标事件），不用 `match: text`（JS .click()）。

---

## 11. 操作流程总结

编写 STEPS 配置的最快流程：

```
1. 在 Chrome 中打开目标网站
2. 在 Console 中粘贴 inspectEl 代码 → 点击页面元素获取 STEPS 信息
3. 或: 右键点击目标元素 → 检查 → 记录 selector 或 match 参数
4. 在 Console 中验证: verifyClick("选择器") — 确认 CDP 点击能命中目标
5. 执行搜索 → 定位结果链接 → 记录 selector 或 match 参数
6. 编写 STEPS 配置 → 运行 auto 模式测试
```

5分钟完成配置，比 discover 模式快得多。

---

## 相关文档

- [选择器入门指南](selector-guide.md) — CSS 选择器语法详解（面向非前端开发者）
- [Action 类型详解](actions.md) — STEPS 中所有 action 的参数说明
- [README 第7章](../README.md) — 元素定位方式总览（selector vs match）