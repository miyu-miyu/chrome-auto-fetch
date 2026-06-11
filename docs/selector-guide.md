# CSS 选择器入门指南

本文档面向**不熟悉前端开发**的用户，帮助你理解什么是 CSS 选择器、怎么写、以及如何用它定位网页上的元素（输入框、按钮、链接等）来编写 STEPS 配置。

---

## 1. 什么是 CSS 选择器

网页是一个 HTML 文档，里面有很多"元素"——按钮、输入框、链接、图片等。每个元素都有标签名和各种属性：

```html
<input id="search-input" name="query" type="text" placeholder="搜索项目" class="form-input">
<button id="search-btn" class="btn primary" aria-label="搜索">搜索</button>
<a href="/openharmony" class="link" title="OpenHarmony项目">OpenHarmony字节码分析工具</a>
```

CSS 选择器就是**用来描述"我要找哪个元素"的一套语法规则**。你写一段选择器字符串，浏览器就能在整张页面中找到匹配的元素。

chrome-auto-fetch 的 `selector` 参数接收的就是这种选择器字符串，底层通过 `document.querySelector(selector)` 在页面上查找元素。

---

## 2. 最常用的 6 种选择器

### 2.1 ID 选择器 — `#id`

用元素的 `id` 属性定位。id 在整张页面中应该是唯一的，所以这是**最精确、最推荐**的方式。

```html
<input id="search-input">
```

```yaml
- action: fill
  selector: "#search-input"
  content: "OpenHarmony"
```

写法：`#` + id 值，不要加引号。

| HTML | 选择器 |
|---|---|
| `<input id="email">` | `#email` |
| `<div id="login-form">` | `#login-form` |
| `<button id="submit-btn">` | `#submit-btn` |

> **Discovery 输出中标注 ★ 的 `#xxx` 选择器就是 ID 选择器，优先使用。**

### 2.2 Class 选择器 — `.class`

用元素的 `class` 属性定位。class 可以有多个值（空格分隔）。

```html
<button class="btn primary">
```

```yaml
- action: click
  selector: ".btn.primary"
```

写法：`.` + class 值。多个 class 串联写（不加空格）表示"同时拥有所有这些 class"。

| 含义 | 选择器 | 匹配 |
|---|---|---|
| 拥有 class="btn" 的元素 | `.btn` | `<button class="btn">` |
| 同时拥有 btn 和 primary 的元素 | `.btn.primary` | `<button class="btn primary">` |
| 拥有 class="link" 的 `<a>` 标签 | `a.link` | `<a class="link">` |

> ⚠️ 单个 class 可能匹配多个元素（Discovery 中标注 ○ 的就是这种情况）。多个 class 串联可以缩小范围，但不保证唯一。优先用 ★ 标记的选择器。

### 2.3 标签选择器 — `tagname`

直接用 HTML 标签名。**通常不够精确**（一张页面有几十个 `<input>`、上百个 `<a>`），一般要和属性选择器组合使用。

```yaml
- action: click
  selector: "button"
```

| 标签 | 选择器 | 说明 |
|---|---|---|
| `<input>` | `input` | 输入框 |
| `<button>` | `button` | 按钮 |
| `<a>` | `a` | 链接 |
| `<select>` | `select` | 下拉框 |
| `<textarea>` | `textarea` | 多行文本框 |
| `<div>` | `div` | 容器区块 |

### 2.4 属性选择器 — `[attr='value']`

用元素的任意 HTML 属性定位。这是**最灵活**的方式——可以匹配任何属性（不仅仅是 id 和 class）。

```html
<input name="query" placeholder="搜索项目" type="email" data-testid="search-input">
```

```yaml
# 按 name 属性
- action: fill
  selector: "[name='query']"
  content: "OpenHarmony"

# 按 placeholder 属性
- action: fill
  selector: "[placeholder='搜索项目']"
  content: "OpenHarmony"

# 按 type 属性
- action: fill
  selector: "input[type='email']"
  content: "test@example.com"

# 按 data-testid 自定义属性
- action: fill
  selector: "[data-testid='search-input']"
  content: "OpenHarmony"

# 按 href 属性（匹配链接）
- action: click
  selector: "a[href='/openharmony']"
```

写法：`[属性名='属性值']`，属性值用**单引号**包裹。

**标签 + 属性组合**：在属性选择器前面加标签名，缩小匹配范围：

| 选择器 | 含义 |
|---|---|
| `[placeholder='搜索']` | 页面上任意拥有此 placeholder 的元素 |
| `input[placeholder='搜索']` | 只有 `<input>` 标签中拥有此 placeholder 的元素 |
| `a[href='/download']` | 只有 `<a>` 标签中拥有此 href 的元素 |
| `button[aria-label='搜索']` | 只有 `<button>` 标签中拥有此 aria-label 的元素 |

**多属性组合**：串联多个属性选择器，同时满足所有条件：

```yaml
# name 为 query 且 type 为 text 的输入框
- action: fill
  selector: "input[name='query'][type='text']"
  content: "OpenHarmony"

# class 包含 form-input 且 autocomplete 为 email 的输入框
- action: fill
  selector: ".form-input[autocomplete='email']"
  content: "test@example.com"
```

#### 属性选择器的 4 种匹配模式

除了精确匹配 `[attr='val']`，还有其他匹配模式：

| 语法 | 含义 | 示例 |
|---|---|---|
| `[attr='val']` | 属性值**完全等于** val | `[type='password']` 匹配 `type="password"` |
| `[attr*='val']` | 属性值**包含** val | `[class*='search']` 匹配 `class="header-search-bar"` |
| `[attr^='val']` | 属性值**以** val **开头** | `[href^='https']` 匹配 `href="https://..."` |
| `[attr$='val']` | 属性值**以** val **结尾** | `[href$='.pdf']` 匹配 `href="...file.pdf"` |

> 💡 `*=` 就相当于 match 的 `match_mode: contains`。你可以直接在 selector 中使用，比 match 更灵活（match 只支持 `=` 和 `*=`，selector 还支持 `^=` 和 `$=`）。

#### 常见 HTML 属性速查表

以下是在表单自动化中最常用的 HTML 属性：

| 属性 | 作用 | 常见元素 | 示例 |
|---|---|---|---|
| `id` | 元素唯一标识 | 所有元素 | `id="search-input"` |
| `name` | 表单字段名（提交数据用） | input, select, textarea | `name="username"` |
| `type` | 输入框类型 | input | `type="text"` / `type="password"` / `type="email"` |
| `placeholder` | 输入框占位提示文字 | input, textarea | `placeholder="搜索项目"` |
| `class` | 样式类名 | 所有元素 | `class="btn primary"` |
| `href` | 链接目标地址 | a | `href="/download"` |
| `aria-label` | 无障碍描述文字 | 所有元素 | `aria-label="搜索"` |
| `title` | 鼠标悬停提示文字 | 所有元素 | `title="点击下载"` |
| `role` | 无障碍角色 | 所有元素 | `role="button"` |
| `data-*` | 自定义数据属性 | 所有元素 | `data-testid="email-input"` |
| `autocomplete` | 浏览器自动填充类型 | input | `autocomplete="email"` |
| `value` | 元素当前值 / 默认值 | input, button | `value="提交"` |
| `disabled` | 禁用状态 | input, button | `disabled` |
| `required` | 必填标记 | input | `required` |

### 2.5 层级选择器 — 父子关系

当多个元素属性完全相同，但属于不同的父容器时，可以通过层级关系区分。

#### 空格 — 后代选择器（任意层级）

```html
<div class="section-a">
  <div class="wrapper">
    <button class="btn">目标1</button>
  </div>
</div>
<div class="section-b">
  <button class="btn">目标2</button>
</div>
```

```yaml
# section-a 下的 btn（不管中间隔了多少层）
- action: click
  selector: "div.section-a .btn"

# section-b 下的 btn
- action: click
  selector: "div.section-b .btn"
```

写法：`父选择器 子选择器`，中间用**空格**分隔。子元素可以在任意深度。

#### `>` — 直接子代选择器（只匹配下一层）

```html
<ul class="nav">
  <li>首页</li>       ← 直接子代
  <li>
    <ul>
      <li>子菜单</li>  ← 不是直接子代（是孙代）
    </ul>
  </li>
</ul>
```

```yaml
# 只匹配 nav 的直接子 li（首页那一层）
- action: click
  selector: "ul.nav > li"
```

写法：`父选择器 > 子选择器`，中间用 `>` 分隔。只匹配**紧接着的下一层**，不匹配更深的嵌套。

### 2.6 位置选择器 — nth-child / nth-of-type

当同一层级下有多个相同类型的元素，无法通过属性区分时，用位置编号选择。

```html
<div class="results">
  <div class="item">第1条结果</div>
  <div class="item">第2条结果</div>
  <div class="item">第3条结果</div>
</div>
```

```yaml
# 第1条结果
- action: click
  selector: "div.item:nth-of-type(1)"

# 第2条结果
- action: click
  selector: "div.item:nth-of-type(2)"

# 最后一条结果
- action: click
  selector: "div.item:last-of-type"
```

| 选择器 | 含义 |
|---|---|
| `:nth-of-type(N)` | 同类型中的第 N 个（1 开始计数） |
| `:first-of-type` | 同类型中的第一个 |
| `:last-of-type` | 同类型中的最后一个 |
| `:nth-child(N)` | 所有子元素中的第 N 个（不区分类型） |

> ⚠️ 位置选择器依赖页面结构不变，页面改版后编号可能变化。**只作为兜底方案使用**——优先用 id、属性选择器或层级选择器。

---

## 3. 组合实战 — 解决常见定位问题

### 问题 1：多个输入框属性相同，只靠父容器区分

```html
<div class="login-form">
  <input name="email" type="text">
</div>
<div class="signup-form">
  <input name="email" type="text">
</div>
```

两个 `input[name='email']` 属性完全一样，但属于不同的表单：

```yaml
- action: fill
  selector: "div.login-form input[name='email']"
  content: "user@example.com"
```

### 问题 2：按钮没有 id/name，只有 class 和文字

```html
<button class="btn">搜索</button>
<button class="btn">重置</button>
```

用 `match: text` 更方便（不需要猜 class 是不是唯一）：

```yaml
- action: click
  match: text
  value: "搜索"
  tag: "button"
```

或者如果你知道 class 的组合唯一：

```yaml
- action: click
  selector: "button.btn.search-btn"
```

### 问题 3：输入框只有 placeholder，没有 name 和 id

```html
<input placeholder="请输入手机号">
```

用属性选择器或 match 都可以：

```yaml
# 方式一：selector 属性选择器
- action: fill
  selector: "[placeholder='请输入手机号']"
  content: "13800138000"

# 方式二：match（更简洁）
- action: fill
  match: placeholder
  value: "请输入手机号"
  content: "13800138000"
```

### 问题 4：链接列表中点击特定一个

```html
<div class="search-results">
  <a href="/kernel_linux_6.6">Linux Kernel 6.6</a>
  <a href="/openharmony">OpenHarmony字节码分析工具</a>
  <a href="/harmonyos">HarmonyOS SDK</a>
</div>
```

用 href 属性最精确：

```yaml
- action: click
  selector: "a[href='/openharmony']"

# 或用 match（更简洁）
- action: click
  match: href
  value: "openharmony"
  match_mode: contains
```

### 问题 5：深层嵌套的元素

```html
<div id="app">
  <div class="main-content">
    <div class="search-panel">
      <form class="search-form">
        <input name="q" type="text" placeholder="搜索">
      </form>
    </div>
  </div>
</div>
```

不需要写完整路径！只要最终能唯一确定元素就行：

```yaml
# 简洁写法：直接用 name 属性（如果 name 是唯一的）
- action: fill
  selector: "input[name='q']"
  content: "OpenHarmony"

# 如果 name 不唯一，加层级限定
- action: fill
  selector: "#app input[name='q']"
  content: "OpenHarmony"
```

### 问题 6：自定义 data 属性（data-testid 等）

现代前端框架经常用 `data-testid` 作为测试定位标记：

```html
<input data-testid="email-input" type="email">
<button data-testid="submit-button">提交</button>
```

```yaml
- action: fill
  selector: "[data-testid='email-input']"
  content: "test@example.com"

- action: click
  selector: "[data-testid='submit-button']"
```

### 问题 7：CSS 选择器无法匹配文本内容 — 通过父元素属性间接定位

CSS 选择器只能匹配 HTML **属性**，不能匹配元素的**可见文本内容**。没有 `[text='log']` 这种语法。

```html
<td ng-click="downloadReleaseFolder(item, 'solution', 'log')">
  <span class="folderStyle">log</span>
</td>
```

如果你想点击文本为 "log" 的那个 span，但 `class="folderStyle"` 不唯一（页面上多个 span 都有这个 class），怎么办？

**方法：用父元素的属性间接定位**。父 td 的 `ng-click` 属性值包含 `'log'`，恰好和 span 的文本对应：

```yaml
# 通过父 td 的 ng-click 属性（包含 'log'）间接定位子 span
- action: click
  selector: "td[ng-click*='log'] span.folderStyle"
```

这比精确匹配 span 的文本更实用 — 因为 CSS 选择器根本做不到匹配文本。

**如果还需要限定在第 N 行**，加上行选择器：

```yaml
# 第3行中，ng-click 包含 'log' 的 td 下面的 span.folderStyle
- action: click
  selector: "table tbody tr:nth-of-type(3) td[ng-click*='log'] span.folderStyle"
```

**也可以用 `match: text` 匹配文本**，但不支持限定行号范围：

```yaml
# 匹配文本为 "log" 的 span（不限行号，匹配页面上第一个）
- action: click
  match: text
  value: "log"
  tag: "span"
```

**总结：当目标元素的 class 不唯一、且需要按文本内容区分时，有两种策略：**

| 策略 | 写法 | 优点 | 缺点 |
|---|---|---|---|
| 父元素属性间接定位 | `td[ng-click*='log'] span.folderStyle` | 可限定行号范围 | 需要父元素有独特属性 |
| match: text | `match: text, value: "log"` | 直接匹配文本，简单 | 不能限定行号范围 |

### 问题 8：表格中定位特定行特定列的单元格

表格操作是最常见的复杂定位场景。结合行号、列属性、子元素三层定位：

```html
<table>
  <thead>
    <tr><th>名称</th><th>版本</th><th>下载</th></tr>
  </thead>
  <tbody>
    <tr>
      <td>Linux Kernel</td>
      <td>6.6</td>
      <td ng-click="download('kernel')"><span class="folderStyle">kernel</span></td>
    </tr>
    <tr>
      <td>OpenHarmony</td>
      <td>4.0</td>
      <td ng-click="download('log')"><span class="folderStyle">log</span></td>
    </tr>
  </tbody>
</table>
```

```yaml
# 第1行第1列（名称）
- action: click
  selector: "table tbody tr:nth-of-type(1) td:nth-of-type(1)"

# 第2行中 ng-click 包含 'log' 的单元格下的 span
- action: click
  selector: "table tbody tr:nth-of-type(2) td[ng-click*='log'] span.folderStyle"

# 任意行中文本为 "log" 的 span（不限行号）
- action: click
  match: text
  value: "log"
  tag: "span"
```

**表格定位三层模板：`行选择器 + 列选择器 + 目标元素选择器`**

```
table tbody tr:nth-of-type(N)  →  定位到第 N 行
td:nth-of-type(M) 或 td[attr*='val']  →  定位到第 M 列或有特定属性的列
span.classname  →  定位到单元格内的具体元素
```

---

## 4. selector 和 match 的对比与选择

| | `selector` | `match` |
|---|---|---|
| 语法 | CSS 选择器字符串 | 关键字 + 值 |
| 匹配范围 | 任意 HTML 属性、层级、组合 | 5 种固定属性 + text |
| **文本内容匹配** | ❌ CSS 选择器无法匹配可见文本 | ✅ `match: text` 可按文本匹配 |
| 组合条件 | ✅ 串联多个属性 `[a='x'][b='y']` | ❌ 只能单属性匹配 |
| 层级路径 | ✅ `div.parent .child` | ❌ 不支持层级 |
| 位置编号 | ✅ `:nth-of-type(2)` | ❌ |
| 包含匹配 | ✅ `[attr*='val']` | ✅ `match_mode: contains` |
| 开头/结尾匹配 | ✅ `[attr^='val']` `[attr$='val']` | ❌ |
| 范围限定+文本匹配 | ⚠️ 无法直接做；可通过父元素属性间接定位 | ❌ 不支持限定范围后再文本匹配 |
| 学习门槛 | 需要了解 CSS 选择器语法 | 低门槛，写属性名和值即可 |
| 稳定性 | 层级/class 选择器可能因页面改版失效 | 属性值通常比 class 更稳定 |

**选择原则：**

1. 有唯一 `id` → 用 `selector: "#id"`
2. 有独特属性值 → 用 `selector: "[attr='value']"` 或 `match`
3. 属性相同、父容器不同 → 用 `selector: "父 子"`
4. 属性和层级都不够区分 → 用 `selector: "...:nth-of-type(N)"` 或 `match: text`
5. 不想写 CSS 语法 → 用 `match`（简单场景够用）

---

## 5. 如何获取选择器

有三种方式获取选择器，推荐度从高到低：

### 5.1 Chrome DevTools 元素检查器（推荐）

最快的方法 — 在目标网页上右键点击元素 → 检查 → 复制选择器。30秒完成。

详细的操作方法和 Console 辅助命令（inspectEl、verifyClick 等），请参见 **[Chrome DevTools 元素定位指南](devtools-guide.md)**。

### 5.2 Discovery 模式（批量概览）

需要全面了解页面有哪些可交互元素时使用：

```bash
python3 main.py --mode discover --url "https://目标网站"
```

输出中每个元素会列出选择器候选列表，★ 标记 = 已验证唯一（优先使用），○ 标记 = 非唯一。

输出示例：

```
[1] <input>  ★ #golbalSearch   (唯一 ✓)     ← 用这个！
    ★ input[placeholder="搜索项目"]   (唯一 ✓)
    ○ input.search-input   (匹配2个)

[4] <a>  ★ a[href="/openharmony"]   (唯一 ✓)     ← 用这个！
    ○ a.search-card-title   (匹配3个)
```

**从输出中复制 ★ 标记的选择器，直接写进 STEPS 配置即可。**

### 5.3 手动编写（需要掌握本章的选择器语法）

如果前两种方式都不方便，可以根据元素的 HTML 属性手动编写选择器。这需要你理解本章介绍的各种选择器语法。

**三种方式选择原则：**

| 方式 | 适用场景 | 耗时 |
|---|---|---|
| DevTools 检查器 | 定位单个具体元素（搜索框、按钮、结果链接） | 30秒 |
| Discovery 模式 | 需要了解页面整体结构 | 10秒 + 运行等待 |
| 手动编写 | 元素属性已知，或者需要组合多个条件 | 需要语法知识 |

---

## 6. 特殊值处理

### 6.1 属性值中的特殊字符

HTML 属性值如果包含以下字符，在 CSS 选择器中需要特别注意：

| 特殊字符 | 选择器中的处理 | 示例 |
|---|---|---|
| 单引号 `'` | 选择器改用双引号包裹 | `[title="It's a test"]` |
| 双引号 `"` | 选择器改用单引号包裹 | `[placeholder='输入"关键词"']` |
| 反斜杠 `\` | 需要双写 `\\` | `[href='path\\to\\file']` |
| 空格 | 正常使用（值在引号内） | `[placeholder='搜索 项目']` |

> 💡 chrome-auto-fetch 的 discover 模式会自动处理属性值转义，输出的选择器可以直接使用。

### 6.2 href 的相对路径 vs 绝对路径

HTML 中 href 可能是相对路径（`/openharmony`），浏览器会自动转为绝对 URL（`https://gitcode.com/openharmony`）。

CSS 属性选择器匹配的是 **HTML 原始属性值**（相对路径），不是浏览器解析后的绝对 URL：

```html
<a href="/openharmony">OpenHarmony</a>
```

```yaml
# ✅ 正确：用 HTML 中的原始值
- action: click
  selector: "a[href='/openharmony']"

# ❌ 错误：用浏览器解析后的绝对 URL
- action: click
  selector: "a[href='https://gitcode.com/openharmony']"

# ✅ 也可以：用包含匹配（不关心完整路径）
- action: click
  selector: "a[href*='openharmony']"
```

> 💡 Discovery 输出的 href 选择器使用 `getAttribute('href')` 获取原始值，所以输出的选择器是正确的。

---

## 7. 速查表

### selector 写法速查

| 要匹配 | 写法 | 示例 |
|---|---|---|
| 唯一 ID | `#id` | `#search-input` |
| 拥有某 class | `.class` | `.btn` |
| 同时拥有多个 class | `.a.b` | `.btn.primary` |
| 标签 | `tag` | `button` |
| 标签 + class | `tag.class` | `button.btn` |
| 拥有某属性 | `[attr]` | `[disabled]` |
| 属性值精确匹配 | `[attr='val']` | `[name='query']` |
| 属性值包含 | `[attr*='val']` | `[class*='search']` |
| 属性值以...开头 | `[attr^='val']` | `[href^='https']` |
| 属性值以...结尾 | `[attr$='val']` | `[href$='.pdf']` |
| 多属性组合 | `[a='x'][b='y']` | `input[name='q'][type='text']` |
| 标签 + 属性组合 | `tag[attr='val']` | `input[placeholder='搜索']` |
| 后代（任意深度） | `父 子` | `div.form input` |
| 直接子代 | `父 > 子` | `ul.nav > li` |
| 第 N 个同类型 | `:nth-of-type(N)` | `div.item:nth-of-type(2)` |
| 第一个同类型 | `:first-of-type` | `div.item:first-of-type` |
| 最后一个同类型 | `:last-of-type` | `div.item:last-of-type` |

### fill 的三种写法速查

```yaml
# 模式一：params 字典（一次性填多个字段）
- action: fill
  params:
    "#username": "admin"
    "#password": "123456"

# 模式二：selector + content（填单个字段）
- action: fill
  selector: "#search-input"
  content: "OpenHarmony"

# 模式三：match + value + content（按属性匹配后填入）
- action: fill
  match: placeholder
  value: "搜索项目"
  content: "OpenHarmony"
```

### click 的三种写法速查

```yaml
# 方式一：selector
- action: click
  selector: "#search-btn"

# 方式二：match 属性匹配
- action: click
  match: href
  value: "/openharmony"

# 方式三：match: text 文本匹配
- action: click
  match: text
  value: "搜索"
  tag: "button"
```