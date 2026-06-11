# Action 类型详解

本文档是 chrome-auto-fetch 全部 16 种 STEPS action 类型的完整参考手册。内容基于 `src/step_engine.py` 的实现细节和 README 第 6 章的描述整理而成。每个 action 均包含参数表、YAML 示例、进阶用法和注意事项。

若对元素定位方式 (`match` / `selector`) 不熟悉, 请先阅读 README 第 7 章 "元素定位方式" 和 **[选择器入门指南](selector-guide.md)**。

---

## 目录

- [navigate](#navigate)
- [fill](#fill)
- [click](#click)
- [click_at](#click_at)
- [type_text](#type_text)
- [press_key](#press_key)
- [wait](#wait)
- [evaluate](#evaluate)
- [extract](#extract)
- [loop](#loop)
- [branch](#branch)
- [screenshot](#screenshot)
- [snapshot](#snapshot)
- [new_page](#new_page)
- [list_pages](#list_pages)
- [save](#save)

---

## navigate

### 描述

导航到指定的 URL。打开一个新页面或在当前页面跳转到目标地址。

### 参数

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `action` | string | 是 | — | 必须为 `navigate` |
| `url` | string | 是 | — | 目标网址, 支持 `${变量名}` 引用 |
| `delay` | number | 否 | `STEP_DELAY` (默认 2s) | 导航完成后的等待秒数 |
| `name` | string | 否 | — | 步骤标签, 用于日志和 branch 引用 |
| `on_fail` | string | 否 | `abort` | 失败处理策略: `abort` / `skip` / `retry(N)` |

### 基本用法

```yaml
- action: navigate
  url: "https://example.com/search"
```

### 进阶用法

```yaml
# 使用变量引用
- action: evaluate
  expr: "'https://example.com/search?q=test'"
  save_to: "search_url"

- action: navigate
  url: "${search_url}"

# 自定义延迟 (等待页面渲染完成)
- action: navigate
  url: "https://example.com/slow-page"
  delay: 5

# 带 name 标签, 便于 branch 引用和日志定位
- action: navigate
  url: "https://example.com/login"
  name: "open_login"
```

### 注意事项

- `url` 参数支持 `${变量名}` 语法, 会在执行前被替换为变量的实际值
- 延迟默认使用配置中的 `STEP_DELAY` (默认 2 秒), 覆盖后只影响当前步骤
- 如果页面加载缓慢, 可以增大 `delay` 值给渲染留出时间; 更可靠的方案是在后续使用 `wait` action 等待特定条件达成

---

## fill

### 描述

向页面中的输入框或下拉框填入文本内容。支持三种模式: 

- 模式一：`params` 字典模式
- 模式二：`selector + content` 模式
- 模式三：`match` 属性匹配模式 (用 `value` 搜索匹配, `content` 指定填入内容)。

### 参数

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `action` | string | 是 | — | 必须为 `fill` |
| `params` | dict | 否 | `{}` | 键值对: CSS 选择器 → 填入值 (模式一) |
| `selector` | string | 否 | — | CSS 选择器, 配合 `content` 使用 (模式二) |
| `content` | string | 条件必填 | — | 填入的值 (模式二/模式三)。使用模式二或模式三时必填 |
| `value` | string | 条件必填 | — | **匹配搜索值** (仅模式三)。如 `match: placeholder, value: "搜索项目"` 表示用 "搜索项目" 去匹配 placeholder 属性。使用 match 时必填 |
| `match` | string | 否 | — | 属性匹配类型: `href` / `aria_label` / `aria-label` / `name` / `placeholder` / `text` (模式三) |
| `tag` | string | 否 | `""` | 限定搜索的 HTML 标签 (仅 `match: text` 时有效) |
| `match_mode` | string | 否 | `exact` | 匹配精度: `exact` (完全匹配) / `contains` (包含匹配) |
| `delay` | number | 否 | 0.5 | 填入后的等待秒数 |
| `name` | string | 否 | — | 步骤标签 |
| `on_fail` | string | 否 | `abort` | 失败处理策略 |

### 基本用法

```yaml
# 模式一: params 字典 (一次性填入多个字段)
- action: fill
  params:
    "#model": "Mate60 Pro"
    "#version": "HarmonyOS 4.0"
    "#region": "中国"

# 模式二: selector + content (单个字段)
- action: fill
  selector: "#search-input"
  content: "OpenHarmony"
```

### 进阶用法

```yaml
# 模式三: match 属性匹配 (按 name 属性定位)
- action: fill
  match: name
  value: "query"
  content: "OpenHarmony"

# 模式三: match 按 placeholder 定位
- action: fill
  match: placeholder
  value: "搜索项目"
  content: "OpenHarmony"

# 模式三: match 按文本内容定位输入框
# 只在 INPUT/TEXTAREA 元素上有效, 其他标签会报错
- action: fill
  match: text
  value: "请输入搜索内容"
  content: "OpenHarmony"

# 模式三: match:text 配合 tag 缩小范围 + contains 模式
- action: fill
  match: text
  value: "搜索"
  tag: "input"
  match_mode: contains
  content: "HarmonyOS"

# 变量引用填入
- action: evaluate
  expr: "'HarmonyOS 4.0'"
  save_to: "version"

- action: fill
  params:
    "#version": "${version}"
```

### 注意事项

- `params`、`selector`、`match` 三者不能混用。优先级: `match` > `params` > `selector`
- 当 `match` 存在时, `selector` 被忽略
- `match: text` 在 fill 中仅对 `<INPUT>` 和 `<TEXTAREA>` 元素有效。如果找到匹配文本的元素但不是输入框, 步骤会失败返回 `ERROR:element found but not an input`
- `match: text` 的底层使用 JS 设置 `el.value` 并派发 `input` 和 `change` 事件, 能触发大部分前端框架的响应
- `match` 为非 text 类型 (href/aria_label/name/placeholder) 时, 直接使用 `cli.fill(selector, content)` 通过 CSS 属性选择器定位
- `match_mode: contains` 在属性类型中使用 CSS `*=`, 在 text 类型中使用 JS `.includes()`
- `content` 和 `value` 语义完全不同: `content` 是填入值 (填进输入框的内容), `value` 是匹配搜索值 (match 用来定位元素的属性值)。两者不应混淆
- 在 `match` 模式下, `value` 是必填的匹配搜索值, `content` 是必填的填入值; 不存在兜底关系
- 详见元素定位方式 (README 第 7 章)

---

## click

### 描述

点击页面上的元素。支持 CSS 选择器定位、属性匹配定位 (`match`)、和文本匹配定位 (`match: text`)。可选择点击第 N 个或最后一个匹配元素。

### 参数

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `action` | string | 是 | — | 必须为 `click` |
| `selector` | string | 否 | — | CSS 选择器 |
| `match` | string | 否 | — | 属性匹配类型: `href` / `aria_label` / `aria-label` / `name` / `placeholder` / `text` |
| `value` | string | 否 | — | match 的匹配值 |
| `index` | int/string | 否 | `1` | 点击第几个匹配元素: `1` (第一个) / `"last"` (最后一个) / `N` (第 N 个) |
| `tag` | string | 否 | `""` | 限定搜索的 HTML 标签 (仅 `match: text` 时有效) |
| `match_mode` | string | 否 | `exact` | 匹配精度: `exact` / `contains` |
| `delay` | number | 否 | `STEP_DELAY` (默认 2s) | 点击后的等待秒数 |
| `name` | string | 否 | — | 步骤标签 |
| `on_fail` | string | 否 | `abort` | 失败处理策略 |

### 基本用法

```yaml
# CSS 选择器点击
- action: click
  selector: "#search-btn"

# 点击第一个匹配的元素 (默认 index=1)
- action: click
  selector: ".result-item a"
```

### 进阶用法

```yaml
# 使用 index 点击第二个结果
- action: click
  selector: ".result-item a"
  index: 2

# 点击最后一个匹配元素
- action: click
  selector: ".file-item .download-btn"
  index: "last"

# 使用 match 按 href 精确匹配
- action: click
  match: href
  value: "https://example.com/download/file.zip"

# 使用 match 按 href 部分匹配
- action: click
  match: href
  value: "download"
  match_mode: contains

# 使用 match 按 aria-label 匹配
- action: click
  match: aria_label
  value: "搜索"

# 使用 match:text 按按钮文字点击
- action: click
  match: text
  value: "登录"

# match:text 配合 tag 缩小范围 + exact 模式
- action: click
  match: text
  value: "确认删除"
  tag: "button"
  match_mode: exact

# match 和 selector 共存时, selector 被忽略
- action: click
  selector: "#some-btn"          # 被忽略
  match: text
  value: "提交"                  # 实际生效的定位方式

# 变量引用
- action: click
  selector: ".${item_class}"
```

### 注意事项

- `match` 和 `selector` 同时存在时, `match` 优先, `selector` 被忽略 (代码会输出警告日志)
- `index: "last"` 使用 JS 在浏览器端定位, 比 CSS `:last-child` 更可靠
- `index: N` 使用 0-based JS 索引, 所以 `index: 2` 点击的是匹配列表中的第二个元素
- 当 `index` 超出匹配元素范围时, 步骤失败并返回 `ERROR:index N out of range`
- 当 `selector` 为空字符串且没有 `match` 时, 步骤会 `skip_empty_selector` 不执行点击
- `match: text` 点击通过 JS 遍历页面上所有 (或指定 `tag` 的) 元素, 找到文本匹配的第一个元素并调用 `.click()`, 如果都没找到则返回 `ERROR:no element with matching text found`
- 详见元素定位方式 (README 第 7 章)

---

## click_at

### 描述

按屏幕坐标点击页面。与 CSS 选择器无关, 直接用像素坐标定位。

### 参数

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `action` | string | 是 | — | 必须为 `click_at` |
| `x` | int | 是 | — | 横坐标 (像素) |
| `y` | int | 是 | — | 纵坐标 (像素) |
| `delay` | number | 否 | `STEP_DELAY` (默认 2s) | 点击后的等待秒数 |
| `name` | string | 否 | — | 步骤标签 |
| `on_fail` | string | 否 | `abort` | 失败处理策略 |

### 基本用法

```yaml
- action: click_at
  x: 500
  y: 300
```

### 注意事项

- 坐标相对于浏览器视口 (viewport), 不包含浏览器工具栏和地址栏
- 页面滚动时坐标需要相应调整, 不适合页面结构动态变化的场景
- 建议只在 Discovery 模式确认坐标后使用, 或用于点击 Canvas / SVG 等无法用 CSS 选择器定位的元素
- `x` 和 `y` 参数支持 `${变量名}` 引用

---

## type_text

### 描述

在当前聚焦的元素上模拟键盘输入文本。可选的 `submit_key` 参数让输入后自动按下回车等键。

### 参数

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `action` | string | 是 | — | 必须为 `type_text` |
| `text` | string | 是 | — | 要输入的文本内容 |
| `submit_key` | string | 否 | — | 输入后按下的修饰键, 如 `Enter`、`Tab` 等 |
| `delay` | number | 否 | `STEP_DELAY` (默认 2s) | 输入完成后的等待秒数 |
| `name` | string | 否 | — | 步骤标签 |
| `on_fail` | string | 否 | `abort` | 失败处理策略 |

### 基本用法

```yaml
# 单纯输入文本
- action: type_text
  text: "OpenHarmony"
```

### 进阶用法

```yaml
# 输入后按回车提交
- action: type_text
  text: "搜索内容"
  submit_key: "Enter"

# 输入后按 Tab 跳到下一个输入框
- action: type_text
  text: "用户名"
  submit_key: "Tab"
```

### 注意事项

- 需要先通过 `click` 或 `fill` 将焦点设置到目标元素上
- `submit_key` 的值是键盘键名, 常见值: `Enter`、`Tab`、`Escape`
- `text` 和 `submit_key` 均支持 `${变量名}` 引用

---

## press_key

### 描述

模拟按下键盘上的某个键 (不涉及文本输入)。

### 参数

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `action` | string | 是 | — | 必须为 `press_key` |
| `key` | string | 是 | — | 键名, 如 `Escape`、`Enter`、`Tab`、`ArrowDown` |
| `delay` | number | 否 | `STEP_DELAY` (默认 2s) | 按键后的等待秒数 |
| `name` | string | 否 | — | 步骤标签 |
| `on_fail` | string | 否 | `abort` | 失败处理策略 |

### 基本用法

```yaml
# 关闭弹窗/对话框
- action: press_key
  key: "Escape"

# 提交表单
- action: press_key
  key: "Enter"
```

### 进阶用法

```yaml
# 翻页 / 下拉加载更多
- action: press_key
  key: "PageDown"

# 变量引用键名
- action: evaluate
  expr: "'Escape'"
  save_to: "close_key"

- action: press_key
  key: "${close_key}"
```

### 注意事项

- 按键事件发送到当前聚焦的元素上, 确保目标元素已获得焦点
- 常用键名: `Escape`、`Enter`、`Tab`、`ArrowDown`、`ArrowUp`、`ArrowLeft`、`ArrowRight`、`PageDown`、`PageUp`、`Home`、`End`、`Delete`、`Backspace`
- `key` 参数支持 `${变量名}` 引用

---

## wait

### 描述

等待某个条件满足后继续执行。支持 5 种策略: `text`、`element`、`url_change`、`js`、`timeout`。所有策略均支持 `timeout` 参数, 超时后步骤失败。

### 参数

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `action` | string | 是 | — | 必须为 `wait` |
| `strategy` | string | 否 | `timeout` | 等待策略: `text` / `element` / `url_change` / `js` / `timeout` |
| `timeout` | int | 否 | 15000 | 超时时间 (毫秒) |
| 策略专属参数 | — | 见下 | — | 不同策略需要不同的参数 |

### 各策略参数

#### text — 等待页面出现指定文本

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `value` | string | 是 | 要等待出现的文本内容 |
| `timeout` | int | 否 | 超时毫秒数 (默认 15000) |

```yaml
- action: wait
  strategy: text
  value: "搜索结果"
  timeout: 15000
```

底层通过 `cli.wait_for(value, timeout_ms=timeout)` 实现 (CDP `Runtime.evaluate` 轮询文本出现)。

#### element — 等待 CSS 选择器匹配的元素出现在 DOM 中

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `selector` | string | 是 | CSS 选择器 |
| `timeout` | int | 否 | 超时毫秒数 (默认 15000) |

```yaml
- action: wait
  strategy: element
  selector: ".download-panel"
  timeout: 10000
```

底层通过 JS `document.querySelector(selector) !== null` 每 500ms 轮询检查。

#### url_change — 等待浏览器 URL 发生变化 (页面跳转)

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `timeout` | int | 否 | 超时毫秒数 (默认 15000) |

```yaml
- action: wait
  strategy: url_change
  timeout: 10000
```

底层通过 JS `window.location.href` 每 500ms 轮询, 与初始 URL 比对。

#### js — 等待 JS 表达式返回 truthy 值

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `expr` | string | 是 | JS 表达式 |
| `timeout` | int | 否 | 超时毫秒数 (默认 15000) |

```yaml
- action: wait
  strategy: js
  expr: "document.querySelectorAll('.result-item').length >= 10"
  timeout: 20000
```

truthy 判断: 返回值不为空, 且不在 `false`、`null`、`undefined`、`0`、`NaN`、`""` 列表中。

#### timeout — 固定等待指定时长

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `timeout` | int | 是 | 等待毫秒数 |

```yaml
- action: wait
  strategy: timeout
  timeout: 3000
```

直接用 `time.sleep()` 实现, 不进行任何条件检测。

### 注意事项

- `text` 和 `element` 策略等待的是**状态变为 true** 的那一刻, 超时即失败
- `url_change` 仅检测当前页面 URL 是否改变 (包括 hash 变化), 不检测新页面打开
- `js` 策略的 truthy 判断排除 `false` / `null` / `undefined` / `0` / `NaN` / `""`, 确保表达式返回有意义的真值
- `timeout` 默认 15 秒, 对于慢页面可以适当增大 (如 30000)
- 超时后的行为取决于 `on_fail` 配置 (默认 `abort` 终止整个流程)

---

## evaluate

### 描述

在浏览器中执行一段 JavaScript 表达式, 并可选地将返回值存入变量供后续步骤使用。

### 参数

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `action` | string | 是 | — | 必须为 `evaluate` |
| `expr` | string | 是 | — | JavaScript 表达式 |
| `save_to` | string | 否 | — | 变量名, 执行结果存入此变量 |
| `name` | string | 否 | — | 步骤标签 |
| `on_fail` | string | 否 | `abort` | 失败处理策略 |

### 基本用法

```yaml
# 直接在页面执行 JS, 返回值不保存
- action: evaluate
  expr: "console.log('hello from auto-fetch')"
```

### 进阶用法

```yaml
# 提取页面信息到变量
- action: evaluate
  expr: "document.title"
  save_to: "page_title"

- action: evaluate
  expr: "document.querySelector('.file-type').textContent.trim()"
  save_to: "file_type"

# 提取动态数据
- action: evaluate
  expr: "window.__INITIAL_STATE__.downloadUrl"
  save_to: "download_url"

# 提取多个值
- action: evaluate
  expr: "JSON.stringify({name: 'test', version: '1.0'})"
  save_to: "metadata"

# 配合 branch 使用
- action: evaluate
  expr: "document.querySelectorAll('.result-item').length"
  save_to: "result_count"

- action: branch
  branches:
    - if: "${result_count} > 0"
      then: 5
    - else: 2
```

### 注意事项

- `save_to` 存入的变量在整个 STEPS 流程中持久存在, 后续步骤可用 `${变量名}` 引用
- 返回值会被 `.strip()` 处理后存入变量, 去除首尾空白
- 表达式可以返回任意 JS 值 (字符串、数字、JSON), 工具会将返回值转为字符串
- 复杂逻辑建议写成 IIFE (立即执行函数表达式): `"(() => { ... })()"`
- 如果不需要保存结果, 省略 `save_to` 即可

---

## extract

### 描述

从页面中提取下载链接 URL。支持 4 种策略: `css`、`js`、`semantic`、`auto` (自动级联)。提取结果可选存入变量。

### 参数

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `action` | string | 是 | — | 必须为 `extract` |
| `strategy` | string | 否 | `auto` | 提取策略: `css` / `js` / `semantic` / `auto` |
| `selector` | string | 否 | — | CSS 选择器 (策略为 `css` 时使用) |
| `expr` | string | 否 | — | JS 表达式 (策略为 `js` 时使用) |
| `save_to` | string | 否 | — | 变量名, 提取的 URL 列表存入此变量 |
| `name` | string | 否 | — | 步骤标签 |
| `on_fail` | string | 否 | `abort` | 失败处理策略 |

### 基本用法

```yaml
# 策略: css — 用 CSS 选择器提取所有匹配元素的 href
- action: extract
  strategy: css
  selector: ".download-btn"

# 策略: js — 用 JS 表达式提取单个 URL
- action: extract
  strategy: js
  expr: "document.querySelector('.download-btn').href"

# 策略: auto — 自动尝试所有方法
- action: extract
  strategy: auto
```

### 进阶用法

```yaml
# 提取多个链接并保存到变量
- action: extract
  strategy: css
  selector: ".file-list a[href]"
  save_to: "download_urls"

# 后续步骤引用变量
- action: evaluate
  expr: "console.log('${download_urls}')"

# JS 提取动态生成的 URL
- action: extract
  strategy: js
  expr: "getDownloadLink()"

# JS 提取 JSON 数组格式的 URL
- action: extract
  strategy: js
  expr: "window.__files__.map(f => f.url)"

# semantic 语义搜索 (不依赖具体选择器)
- action: extract
  strategy: semantic
```

### auto 自动级联逻辑

`strategy: auto` 按以下顺序依次尝试, 一旦某一步提取到 URL 就停止:

1. **CSS 选择器提取** — 如果配置了 `selector`, 用 `document.querySelectorAll(selector)` 提取所有匹配元素的 `href` 属性
2. **JS 表达式提取** — 如果配置了 `expr`, 执行表达式并检查返回值:
   - 以 `http` 开头 → 作为单个 URL
   - JSON 数组 → 作为 URL 列表
3. **语义搜索** — 对页面文本进行正则匹配, 搜索包含 `download` / `file` / `attachment` 关键词的 URL。然后通过 Accessibility Tree 查找包含 "下载" 或 "download" 的节点, 在附近寻找 `<a>` 链接

### 注意事项

- `strategy: css` 仅提取 `<a>` 标签的 `href` 属性, 不提取 `data-url` 或其他自定义属性
- `strategy: js` 返回单个 URL (以 `http` 开头) 会被单独保存; 返回 JSON 数组会展开为 URL 列表
- `strategy: semantic` 是兜底策略, 使用正则匹配, 不够精确但不需要配置选择器
- `save_to` 存入变量的是 URL 列表 (Python list), 可通过 `${变量名}` 在后续 `evaluate` 中使用
- 提取的 URL 会自动去重 (`list(dict.fromkeys(urls))`)
- 详见 README 第 9 章 "下载地址提取方式"

---

## loop

### 描述

循环检查某个条件是否满足, 直到条件满足或达到最大迭代次数。适用于等待异步过程完成 (如进度条 100%、文件生成完成)、虚拟滚动下拉框逐轮滚动加载等场景。

`each` 参数允许在每轮条件检查前执行一组子步骤, 实现"每轮执行动作 → 检查条件"的循环模式。

### 参数

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `action` | string | 是 | — | 必须为 `loop` |
| `condition` | string | 否 | `js` | 检查类型: `js` / `element_exists` / `text_exists` |
| `expr` | string | 否 | — | JS 条件表达式 (condition=`js` 时必填) |
| `selector` | string | 否 | — | CSS 选择器 (condition=`element_exists` 时必填) |
| `value` | string | 否 | — | 文本内容 (condition=`text_exists` 时必填) |
| `each` | list | 否 | — | 每轮条件检查前执行的子步骤列表, 子步骤支持所有 action 类型 |
| `max_iterations` | int | 否 | 30 | 最多循环检查次数 |
| `interval` | int | 否 | 2000 | 每次检查间隔 (毫秒) |
| `on_timeout` | string | 否 | `fail` | 超时后行为: `fail` / `continue` / `extract_and_continue` |
| `name` | string | 否 | — | 步骤标签 |
| `on_fail` | string | 否 | `abort` | 失败处理策略 |

### 基本用法

```yaml
# condition: js — 等待 JS 表达式返回 truthy
- action: loop
  condition: js
  expr: "document.querySelector('.progress').textContent.includes('100%')"
  max_iterations: 60
  interval: 2000
  on_timeout: fail
```

### each: 每轮执行子步骤

`each` 参数接受一个子步骤列表, 在每轮条件检查**前**执行。每轮的执行顺序:

```
第1轮: 执行 each 子步骤 → 检查 condition → 不满足 → sleep(interval)
第2轮: 执行 each 子步骤 → 检查 condition → 不满足 → sleep(interval)
...
第N轮: 执行 each 子步骤 → 检查 condition → 满足 → 返回成功
```

子步骤支持所有 action 类型 (evaluate, click, fill, wait 等), 子步骤失败不会终止 loop, 只会跳过该子步骤继续执行。子步骤的 `save_to` 结果存入 variables, 供后续轮次或主流程使用。

**典型场景: 虚拟滚动下拉框** — 下拉框列表很长, 目标选项不在 DOM 中, 需要每轮滚动容器让新选项加载到 DOM, 然后检查目标选项是否出现:

```yaml
# 先点击展开下拉框
- action: click
  selector: ".dropdown-trigger"

- action: wait
  strategy: element
  selector: ".dropdown-menu"

# 循环滚动下拉框, 直到目标选项出现在 DOM 中
- action: loop
  condition: js
  expr: "document.querySelector('.dropdown-menu li[data-value=\"openharmony\"]') !== null"
  max_iterations: 50
  interval: 500
  each:
    - action: evaluate
      expr: "document.querySelector('.dropdown-menu').scrollTop += 200"

# 目标选项已出现, 滚动到可视区域并点击
- action: evaluate
  expr: "document.querySelector('.dropdown-menu li[data-value=\"openharmony\"]').scrollIntoView({block:'center'})"

- action: click
  match: text
  value: "OpenHarmony"
  tag: "li"
```

**子步骤使用 save_to 提取变量** — 每轮提取滚动位置, 供条件表达式使用:

```yaml
- action: loop
  condition: js
  expr: "parseInt(${scroll_pos}) >= 10000"
  max_iterations: 100
  interval: 1000
  each:
    - action: evaluate
      expr: "document.querySelector('.scroll-container').scrollTop.toString()"
      save_to: "scroll_pos"
    - action: evaluate
      expr: "document.querySelector('.scroll-container').scrollTop += 300"
```

### 进阶用法

```yaml
# condition: element_exists — 等待元素出现在 DOM 中
- action: loop
  condition: element_exists
  selector: ".download-complete"
  max_iterations: 30
  interval: 1000

# condition: text_exists — 等待页面中出现指定文本
- action: loop
  condition: text_exists
  value: "处理完成"
  max_iterations: 20
  interval: 3000

# on_timeout: continue — 超时后继续执行后续步骤
- action: loop
  condition: js
  expr: "document.querySelector('.status').textContent === 'done'"
  max_iterations: 10
  interval: 5000
  on_timeout: continue

# on_timeout: extract_and_continue — 超时时自动提取 URL 并保存
- action: loop
  condition: element_exists
  selector: ".download-link"
  max_iterations: 60
  interval: 2000
  on_timeout: extract_and_continue
  save_to: "download_urls"

# each + element_exists: 滚动直到目标元素出现
- action: loop
  condition: element_exists
  selector: ".dropdown-menu li[data-value='openharmony']"
  max_iterations: 50
  interval: 500
  each:
    - action: evaluate
      expr: "document.querySelector('.dropdown-menu').scrollTop += 200"
```

### on_timeout 行为对比

| on_timeout | 行为 |
|------------|------|
| `fail` | 返回失败, 步骤引擎根据 `on_fail` 继续或终止 |
| `continue` | 返回成功, 跳过 loop 继续执行下一步 |
| `extract_and_continue` | 以当前参数调用 `extract` 提取 URL (存入 `变量["download_urls"]`), 然后继续 |

### 注意事项

- `max_iterations * interval` 是总等待时间上限。例如默认值 30 * 2000ms = 60 秒
- `condition: element_exists` 用 `document.querySelector(selector) !== null` 检查, 元素是否存在即可, 不要求可见
- `condition: text_exists` 用 `document.body.textContent.includes(value)` 检查, 在整页文本中搜索
- `condition: js` 的 truthy 判断与 `wait` 的 `js` 策略相同: 排除 `false` / `null` / `undefined` / `0` / `NaN` / `""`
- `extract_and_continue` 是安全的兜底策略, 即使 loop 超时也能尽可能获取已有结果
- loop 自身的 `on_fail` 与步骤级的 `on_fail` 是两套机制, 不要混淆
- `each` 子步骤失败不会终止 loop, 只会跳过当前子步骤继续执行后续子步骤和条件检查
- `each` 子步骤不支持 `branch` (跳转到主流程的其他步骤) 和嵌套 `loop`, 仅支持执行型 action (evaluate, click, fill, wait 等)
- `each` 子步骤中的 `save_to` 会将结果存入主流程的 `variables`, 供后续轮次读取

---

## branch

### 描述

条件分支跳转, 实现 if-elif-else 逻辑。根据 JS 表达式的 truthy 值或 `${变量}` 条件, 跳转到不同的步骤执行。

### 参数

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `action` | string | 是 | — | 必须为 `branch` |
| `branches` | list | 是 | — | 条件分支列表 |
| `branches[].if` | string (JS) | 第一个必须有 | — | 第一个条件表达式 |
| `branches[].elif` | string (JS) | 否 | — | 后续条件表达式 |
| `branches[].then` | int / string | if/elif 项必须有 | — | 条件满足时的跳转目标 (步骤号或 name 标签) |
| `branches[].else` | int / string | 否 | — | 默认跳转目标 (值即目标, 不需要 then 关键字) |
| `name` | string | 否 | — | 步骤标签 |

### 基本用法

```yaml
- action: branch
  branches:
    - if: "document.querySelector('.modal') !== null"
      then: "handle_popup"
    - elif: "document.querySelector('.direct-download') !== null"
      then: "direct_download"
    - else: "save_result"
```

### 进阶用法

```yaml
# 使用步骤号 (1-based) 作为跳转目标
- action: branch
  branches:
    - if: "document.querySelector('.error-msg') !== null"
      then: 8          # 跳转到第 8 步
    - else: 9           # 跳转到第 9 步

# 使用 ${变量} 引用
- action: evaluate
  expr: "document.querySelector('.file-type').textContent.trim()"
  save_to: "file_type"

- action: branch
  branches:
    - if: "${file_type} === 'PDF'"
      then: "pdf_download"
    - elif: "${file_type} === 'ZIP'"
      then: "zip_download"
    - else: "generic_download"

# 纯 if + else, 没有 elif
- action: branch
  branches:
    - if: "document.querySelector('.popup') !== null"
      then: "close_popup"
    - else: "continue"

# 条件不满足且无 else 时, 继续执行下一步
- action: branch
  branches:
    - if: "document.querySelector('.special-case') !== null"
      then: "handle_special"

# 多个 elif
- action: branch
  branches:
    - if: "${status} === 'pending'"
      then: "wait_more"
    - elif: "${status} === 'processing'"
      then: "check_progress"
    - elif: "${status} === 'done'"
      then: "extract_result"
    - else: "handle_error"
```

### 工作原理

1. `branches` 列表按顺序评估每个条件
2. `if` 最先评估, 若为 truthy 则跳转到 `then`, 不再判断后续
3. `if` 为 falsy 则依次评估 `elif`
4. 第一个 truthy 的 `elif` 触发跳转
5. 所有条件都不满足时:
   - 有 `else` → 跳转到 `else` 指定步骤
   - 无 `else` → 继续执行下一个步骤
6. `then` / `else` 可以使用数字步号 (1-based) 或步骤的 `name` 标签

### 跳转目标解析

跳转目标 (`then` / `else` 的值) 的解析规则:

- **字符串且非纯数字**: 在 STEPS 列表中查找 `name` 匹配的步骤。找到后跳转到该步骤
- **数字或纯数字字符串**: 作为 1-based 步骤索引, `1` 表示第一个步骤

### 注意事项

- `branches` 列表必须至少包含一个 `if` 项, 否则报错 `branches missing if clause`
- `if` / `elif` 表达式在执行前会先进行 `${变量}` 替换
- **branch 不触发 `on_fail`**: branch 永远返回 `success=True`, 无匹配条件是预期行为, 不会终止流程
- 跳转目标超出 STEPS 范围时 (数字越界或 name 标签不存在), 返回 success 但不执行跳转
- 强烈建议为每个步骤添加 `name` 标签, 让 branch 配置更可读且易于维护
- 步骤号使用 1-based (配置中看到的序号), 不是 0-based
- 详见 README 第 6.10 节 "Branch 条件分支跳转"

---

## screenshot

### 描述

截取当前页面的截图, 保存为 PNG 文件。

### 参数

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `action` | string | 是 | — | 必须为 `screenshot` |
| `output` | string | 否 | 自动生成 | 截图保存路径。不指定则自动生成 `result_YYYYMMDD_HHMMSS.png` 到 `OUTPUT_DIR` |
| `name` | string | 否 | — | 步骤标签 |
| `on_fail` | string | 否 | `abort` | 失败处理策略 |

### 基本用法

```yaml
- action: screenshot
```

### 进阶用法

```yaml
# 指定保存路径
- action: screenshot
  output: "/tmp/debug_screenshot.png"

# 在关键步骤后截图用于调试
- action: click
  selector: "#search-btn"

- action: screenshot

- action: wait
  strategy: element
  selector: ".result-list"
```

### 注意事项

- 自动生成的路径为: `OUTPUT_DIR / result_YYYYMMDD_HHMMSS.png`
- 截图覆盖整个视口 (viewport), 不包括滚动区域外的内容
- 截图的文件名时间戳是步骤执行时的系统时间

---

## snapshot

### 描述

获取当前页面的 Accessibility Tree (无障碍树), 以文本或 JSON 格式输出。可选存入变量供后续分析。

### 参数

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `action` | string | 是 | — | 必须为 `snapshot` |
| `format` | string | 否 | `text` | 输出格式: `text` / `json` |
| `save_to` | string | 否 | — | 变量名, 输出的 Accessibility Tree 存入此变量 |
| `name` | string | 否 | — | 步骤标签 |
| `on_fail` | string | 否 | `abort` | 失败处理策略 |

### 基本用法

```yaml
# 文本格式输出 (适合人类阅读)
- action: snapshot
  format: text

# JSON 格式输出 (适合程序处理)
- action: snapshot
  format: json
```

### 进阶用法

```yaml
# 保存 Accessibility Tree 到变量, 然后在 evaluate 中处理
- action: snapshot
  format: json
  save_to: "tree_data"

# 提取文本格式的快照用于调试
- action: snapshot
  format: text
  save_to: "page_snapshot"

- action: evaluate
  expr: "console.log('${page_snapshot}')"
```

### 注意事项

- `format: text` 使用 `cli.snapshot_text()`, 返回人类可读的树形文本
- `format: json` 使用 `cli.snapshot_json()`, 返回包含 nodes 等字段的结构化数据
- JSON 格式的节点包含 `name`、`role`、`children` 等字段, 可用于 `extract` 的语义搜索
- `save_to` 存入的变量类型取决于 format, text 格式是字符串, json 格式是 Python dict
- 大型页面的 Accessibility Tree 可能非常庞大, 注意日志和变量的内存占用

---

## new_page

### 描述

打开一个新的浏览器标签页, 并导航到指定的 URL。

### 参数

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `action` | string | 是 | — | 必须为 `new_page` |
| `url` | string | 是 | — | 新标签页打开的网址 |
| `name` | string | 否 | — | 步骤标签 |
| `on_fail` | string | 否 | `abort` | 失败处理策略 |

### 基本用法

```yaml
- action: new_page
  url: "https://example.com/download"
```

### 进阶用法

```yaml
# 使用变量动态指定 URL
- action: new_page
  url: "${download_url}"
```

### 注意事项

- 新标签页会在当前浏览器窗口中打开, 不会自动切换到该页面
- 新页面打开后, chrome CLI 默认操作的是新激活的页面
- `url` 支持 `${变量名}` 引用
- 与 `navigate` 的区别: `navigate` 在当前页面跳转或使用已有标签页, `new_page` 创建全新标签页

---

## list_pages

### 描述

列出浏览器中当前打开的所有标签页信息 (URL、标题等)。

### 参数

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `action` | string | 是 | — | 必须为 `list_pages` |
| `name` | string | 否 | — | 步骤标签 |
| `on_fail` | string | 否 | `abort` | 失败处理策略 |

### 基本用法

```yaml
- action: list_pages
```

### 注意事项

- 不需要额外参数, 直接列出所有打开的页面
- 输出到日志, 不保存到变量
- 通常用于调试, 确认浏览器中打开了哪些页面
- 多个 `new_page` 或页面跳转后, 可以用此 action 查看当前页面状态

---

## save

### 描述

保存当前提取到的下载链接到结果文件。触发结果数据的收集、去重、写入到 `OUTPUT_DIR` 下的 JSON 和历史文件。

### 参数

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `action` | string | 是 | — | 必须为 `save` |
| `name` | string | 否 | — | 步骤标签 |
| `on_fail` | string | 否 | `abort` | 失败处理策略 |

### 基本用法

```yaml
- action: save
```

### 进阶用法

```yaml
# 提取链接后立即保存
- action: extract
  strategy: css
  selector: ".download-list a"
  save_to: "download_urls"

- action: save

# 可以在流程中多次保存 (提取一批, 保存一批)
- action: extract
  strategy: js
  expr: "getFirstBatchUrls()"
  save_to: "download_urls"

- action: save

- action: extract
  strategy: js
  expr: "getSecondBatchUrls()"
  save_to: "download_urls"

- action: save
```

### 保存机制

`save` 执行时会触发以下流程:

1. `collect_download_urls(result_data, variables)` — 从 `variables["download_urls"]` 收集 URL, 去重
2. `save_result(result_data, config)` — 写入结果文件:
   - `latest_result.json` — 最新结果
   - `history.json` — 累积历史
   - `latest_report.txt` — 文本报告

### 注意事项

- 即使 STEPS 中没有 `save` 步骤, 引擎也会在流程执行完毕后自动保存一次结果
- 如果 STEPS 中包含 `save`, 引擎不会在流程末尾重复保存 (避免重复写入)
- 保存时自动去重 (`list(dict.fromkeys(urls))`)
- 下载 URL 的来源是 `variables["download_urls"]`, 由 `extract` 或 `loop` 的 `extract_and_continue` 填充
- `save` 本身不提取 URL, 只保存已有结果

---

## 典型场景配置示例

### 场景 A: 直接下载（无弹窗）

点击下载按钮后直接触发下载：

```yaml
STEPS:
  - action: navigate
    url: "https://download.example.com/files"
  - action: fill
    params: {"#search": "Mate60"}
  - action: click
    selector: "#search-btn"
  - action: wait
    strategy: element
    selector: ".result-list"
  - action: click
    selector: ".download-btn"
  - action: extract
    strategy: js
    expr: "document.querySelector('.direct-download').href"
    save_to: "download_url"
  - action: save
```

### 场景 B: 弹窗场景

点击搜索结果后弹出弹窗，从弹窗中提取下载链接：

```yaml
STEPS:
  - action: navigate
    url: "https://download.example.com/search"
  - action: fill
    params: {"#model": "Mate60", "#version": "4.0"}
  - action: click
    selector: "#search-btn"
  - action: wait
    strategy: text
    value: "搜索结果"
    timeout: 15000
  - action: click
    selector: ".result-item .link"
    index: 1
  - action: wait
    strategy: element
    selector: ".modal"
  - action: extract
    strategy: css
    selector: ".modal .download-btn"
    save_to: "download_urls"
  - action: click
    selector: ".modal .close-btn"
    on_fail: skip
  - action: save
```

### 场景 C: 循环检查进度条

启动任务后循环检查直到进度完成：

```yaml
STEPS:
  - action: navigate
    url: "https://example.com/process"
  - action: click
    selector: "#start-btn"
  - action: loop
    condition: js
    expr: "document.querySelector('.progress').textContent.includes('100%')"
    max_iterations: 60
    interval: 2000
    on_timeout: fail
  - action: extract
    strategy: css
    selector: ".download-link"
    save_to: "download_urls"
  - action: save
```

### 场景 D: 页面跳转

点击后网页跳转，在新页面提取下载链接：

```yaml
STEPS:
  - action: navigate
    url: "https://example.com/portal"
  - action: fill
    params: {"#username": "admin", "#password": "pass"}
  - action: click
    selector: "#login-btn"
  - action: wait
    strategy: url_change
    timeout: 10000
  - action: click
    selector: ".view-detail-btn"
  - action: wait
    strategy: url_change
    timeout: 5000
  - action: extract
    strategy: js
    expr: "document.querySelector('.download-btn').href"
    save_to: "download_url"
  - action: save
```

### 场景 E: 条件分支 — 根据页面状态跳转

```yaml
STEPS:
  - action: navigate
    url: "https://example.com/search"
    name: "open_search"
  - action: fill
    params: {"#model": "Mate60"}
    name: "fill_params"
  - action: click
    selector: "#search-btn"
    name: "search"
  - action: wait
    strategy: element
    selector: ".result-list"
    name: "wait_results"
  - action: branch
    branches:
      - if: "document.querySelector('.modal') !== null"
        then: "handle_popup"
      - elif: "document.querySelector('.direct-download') !== null"
        then: "direct_download"
      - else: "save_result"
  - action: wait
    strategy: element
    selector: ".modal .download-btn"
    name: "handle_popup"
  - action: extract
    strategy: css
    selector: ".modal .download-btn"
    save_to: "download_urls"
  - action: click
    selector: ".modal .close-btn"
    on_fail: skip
  - action: extract
    strategy: js
    expr: "document.querySelector('.direct-download').href"
    save_to: "download_urls"
    name: "direct_download"
  - action: save
    name: "save_result"
```

### 场景 F: 条件分支 + 变量

先提取文件类型，再根据变量值跳转：

```yaml
STEPS:
  - action: navigate
    url: "https://example.com/files"
    name: "open_files"
  - action: extract
    strategy: js
    expr: "document.querySelector('.file-type').textContent.trim()"
    save_to: "file_type"
    name: "detect_type"
  - action: branch
    branches:
      - if: "${file_type} === 'PDF'"
        then: "pdf_download"
      - elif: "${file_type} === 'ZIP'"
        then: "zip_download"
      - else: "generic_download"
  - action: click
    selector: ".pdf-download-btn"
    name: "pdf_download"
  - action: extract
    strategy: css
    selector: ".pdf-download-btn"
    save_to: "download_urls"
  - action: click
    selector: ".zip-download-btn"
    name: "zip_download"
  - action: extract
    strategy: css
    selector: ".zip-download-btn"
    save_to: "download_urls"
  - action: extract
    strategy: auto
    name: "generic_download"
  - action: save
    name: "save_result"
```

### 场景 G: match 属性匹配

用 match 方式定位元素，不依赖 CSS 选择器层级路径：

```yaml
STEPS:
  - action: navigate
    url: "https://gitcode.com/search?q=OpenHarmony&type=repo"
  - action: fill
    match: placeholder
    value: "搜索项目"
    content: "OpenHarmony"
  - action: click
    match: text
    value: "搜索"
    tag: "button"
  - action: wait
    strategy: text
    value: "搜索结果"
  - action: click
    match: href
    value: "openharmony"
    match_mode: contains
  - action: wait
    strategy: element
    selector: ".detail-panel"
  - action: extract
    strategy: css
    selector: ".detail-panel .download-btn"
    save_to: "download_urls"
  - action: save
```

---

## 附录: 通用参数

以下参数适用于所有 action 类型:

| 参数 | 类型 | 说明 |
|------|------|------|
| `name` | string | 步骤标签, 用于日志显示 (`Step 1/label: action`) 和 branch `then`/`else` 引用 |
| `delay` | number | 步骤执行后的等待秒数。默认值取决于 action 类型: navigate/click/click_at/type_text/press_key 使用 `STEP_DELAY` (默认 2s), fill 固定 0.5s |
| `on_fail` | string | 步骤失败时的处理策略: `abort` (终止, 默认)、`skip` (跳过继续)、`retry(N)` (当前版本等同 abort) |
| `${变量名}` | — | 所有 string 类型的参数值都支持 `${变量名}` 引用, 在执行前被替换为变量的实际值 |

变量通过 `evaluate` 或 `extract` 的 `save_to` 参数写入, 在整个 STEPS 流程中持久存在。
