# chrome-auto-fetch

Chrome DevTools 自动化下载框架：定时从指定网站自动填入参数、检索、点击结果、提取下载地址。

---

## 1. 项目简介

### 1.1 这是什么

chrome-auto-fetch 是一个基于 Chrome DevTools Protocol (CDP) 的自动化下载工具。它能帮你自动完成"打开网站 → 填入搜索条件 → 点击搜索 → 点开结果 → 提取下载链接"这一整套流程，完全不需要人工干预。

你只需要写一份 YAML 配置文件，告诉工具"去哪个网站、填什么内容、点哪个按钮"，剩下的全部自动化完成。

### 1.2 核心特性

| 特性 | 说明 |
|---|---|
| 填空式配置 | 编辑 YAML 配置文件即可，无需写代码 |
| 4 种运行模式 | Discovery / Auto / Cron / Daemon，覆盖从探索到定时执行的全流程 |
| CSS 选择器驱动 | 基于页面元素选择器定位输入框、按钮、结果 |
| 3 种下载提取方式 | CSS 选择器提取 / JS 表达式提取 / 语义搜索自动提取 |
| 连接自动发现 | 自动定位 Chrome DevTools WebSocket 地址，无需手动配置 |
| 跨平台 | macOS / Linux / Windows 全支持 |

### 1.3 架构概览

```
┌─────────────────────────────────────────────────────────────┐
│                   Chrome Debug Instance                      │
│  (独立 profile, 独立端口 9333, 与日常 Chrome 并存)            │
│                                                             │
│  ┌─────────────────┐     ┌──────────────────────────────┐   │
│  │  Target Website  │     │  Chrome DevTools Protocol    │   │
│  │  (目标网页)       │◄───►│  WebSocket API               │   │
│  └─────────────────┘     └──────────┬───────────────────┘   │
└─────────────────────────────────────┼───────────────────────┘
                                      │ CDP WebSocket
                                      │ ws://127.0.0.1:9333/...
                                      ▼
┌─────────────────────────────────────────────────────────────┐
│              chrome-devtools-cli (Rust CLI)                  │
│  将 CDP 命令封装为简洁的命令行: navigate, fill, click,        │
│  evaluate, wait-for, snapshot, screenshot ...                │
└──────────────────────────┬──────────────────────────────────┘
                           │ subprocess 调用
                           ▼
┌─────────────────────────────────────────────────────────────┐
│              chrome-auto-fetch (Python)                      │
│                                                             │
│  main.py  ← CLI 入口, 参数解析, 模式分发                      │
│  src/chrome_cli.py  ← chrome-devtools CLI 的 Python 封装    │
│  src/connection.py  ← 自动发现 WebSocket 连接地址             │
│  src/step_engine.py ← 步骤引擎 (可编排动作序列 + branch 条件跳转 + 安全限制)    │
│  src/discover.py    ← Discovery 模式 (页面结构探索)           │
│  src/result.py      ← 结果保存 (JSON/历史/文本报告)           │
│  src/scheduler.py   ← 定时调度 (cron 生成 + daemon 守护进程)  │
│  config/config.yaml ← 用户配置文件 (YAML 格式, 支持 STEPS)    │
└─────────────────────────────────────────────────────────────┘
```

工作流程:

1. 启动 Chrome 并开启 `--remote-debugging-port=9333`
2. chrome-auto-fetch 通过 WebSocket 连接到 Chrome DevTools Protocol
3. 依次执行用户配置的步骤序列 (STEPS)
4. 支持重试机制 (默认最多 3 次) 和定时调度 (cron / daemon)

---

## 2. 前置条件与安装

chrome-auto-fetch 需要: Python 3.6+, Rust 工具链 (编译 chrome-devtools-cli), Chrome/Chromium, Git, pyyaml。

各平台 (macOS / Linux 多发行版 / Windows) 的详细安装步骤、离线方案、Chrome 远程调试配置, 请参见 **[前置条件与安装指南](docs/INSTALL.md)**。

---

## 3. 快速开始⭐️

环境就绪后, 4 步即可运行:

```bash
# 步骤 1: 启动 Debug Chrome (每次重启电脑后需要重新执行)
# macOS:
bash scripts/start-chrome-debug.sh
# Linux:
bash scripts/start-chrome-debug-linux.sh
# Windows:
scripts\start-chrome-debug.bat

# 步骤 2: 创建配置
cp config/config.example.yaml config/config.yaml

# 步骤 3: 探索页面结构 (获取 CSS 选择器, 编写 STEPS)
python3 main.py --mode discover
# 或手动指定网址:
python3 main.py --mode discover --url "https://example.com/search"

# 步骤 4: 执行自动化流程
python3 main.py --mode auto
```

> **重要**: 步骤 1 是必须的前置操作。Debug Chrome 需要以 `--remote-debugging-port=9333` 参数启动, 才能让工具通过 CDP 控制浏览器。普通启动的 Chrome 无法连接。启动脚本有幂等检查 — 如果 Debug Chrome 已在运行则跳过, 不会重复启动。

配置字段详解见 [第 4 章](#4-配置项目), 运行模式详解见 [第 5 章](#5-使用方式)。

---

## 4. 配置项目

### 4.1 创建配置文件

```bash
cp config/config.example.yaml config/config.yaml
```

### 4.2 配置字段详解

打开 `config/config.yaml`，你会看到以下字段:

| 字段 | 说明 | 必填 |
|---|---|---|
| `CLI_PATH` | chrome-devtools 二进制路径 | 是 |
| `TARGET_URL` | 目标网站 URL (Discovery 模式需要) | 是 |
| `STEPS` | 自定义步骤流程 (核心配置) | 是 |
| `WS_ENDPOINT` | WebSocket URL (留空自动发现) | 否 |
| `USER_DATA_DIR` | Chrome 独立 profile 目录 | 否 |
| `CHANNEL` | Chrome 通道 (stable/beta/canary/dev) | 否 |
| `OUTPUT_DIR` | 输出文件目录 | 否 |
| `LOG_FILE` | 日志文件路径 | 否 |
| `MAX_RETRIES` | 重试次数 (默认 3) | 否 |
| `STEP_DELAY` | 步骤间等待秒数 (默认 2) | 否 |
| `MAX_STEPS` | 步骤数量上限 (默认 100, 硬上限 200) | 否 |
| `MAX_EXECUTIONS` | 运行时执行上限 (默认 500, 硬上限 1000) | 否 |
| `SCHEDULE_TIME` | 定时执行时间 (24h 格式) | 否 |

CLI_PATH 平台默认值:

| 平台 | 默认路径 |
|---|---|
| macOS (Homebrew) | `/usr/local/bin/chrome-devtools` |
| macOS (Cargo 编译) | `target/release/chrome-devtools` |
| Linux | `/usr/local/bin/chrome-devtools` |
| Windows | `chrome-devtools.exe` (需在 PATH 中) |

STEPS 配置详见 [第 6 章](#6-自定义步骤流程-steps)。

---

## 5. 使用方式

### 5.1 Discovery 模式：探索页面可交互元素

Discovery 模式帮你快速了解页面上有哪些可交互元素（输入框、按钮、链接等），以及它们的选择器候选。

```bash
# 使用 config.yaml 中的 TARGET_URL
python3 main.py --mode discover

# 手动指定网址 (不依赖 config.yaml 的 TARGET_URL)
python3 main.py --mode discover --url "https://gitcode.com/search?q=OpenHarmony&type=repo"
```

`--url` 参数适合临时探索某个页面而不想修改 config.yaml。

运行后输出 3 个部分:

1. **可交互元素** — 所有 input、select、button、textarea、a 标签，每个元素显示选择器候选列表 (★ 唯一 / ○ 非唯一)、属性信息 (id, name, placeholder, href, aria-label, text)
2. **STEPS 建议** — 自动提取关键元素（输入框、搜索按钮）的 selector/match 提示 + STEPS 模板
3. **页面截图** — 保存截图用于确认页面结构

输出保存到 `OUTPUT_DIR` 目录:

| 文件 | 内容 | 格式 |
|---|---|---|
| `discovery_elements.json` | 可交互元素数据 (含选择器唯一性验证) | JSON |
| `discovery_screenshot.png` | 页面截图 | 图片 |

### 5.1.1 DevTools 定位方式 (推荐)⭐️

比 discover 更快的方法是**直接在 Chrome DevTools 中检查目标元素**，30 秒就能拿到选择器:

1. 在目标网页上 **右键点击** 要定位的元素 → 选择 **"检查"**
2. 在 DevTools Elements 面板中读取元素的 `id`, `class`, `href`, `aria-label`, `name`, `placeholder`
3. 右键 HTML 代码 → **Copy → Copy selector** → 粘贴到 config.yaml
4. 在 Console 中验证唯一性: `document.querySelectorAll('选择器').length`

示例:

```yaml
# 从 DevTools 中看到 <input id="golbalSearch" placeholder="搜索项目">
- action: fill
  selector: "#golbalSearch"
  content: "OpenHarmony"

# 或者用 match 方式:
- action: fill
  match: placeholder
  value: "搜索项目"
  content: "OpenHarmony"

# 从 DevTools 中看到 <button class="search-btn">搜索</button>
- action: click
  match: text
  value: "搜索"

# 从 DevTools 中看到 <a href="/openharmony/kernel">
- action: click
  match: href
  value: "/openharmony/kernel"
```

DevTools 定位方式的优势:

| 方面 | DevTools | discover 模式 |
|---|---|---|
| 定位精度 | 直达目标元素 | 批量输出，需自行筛选 |
| 操作耗时 | 30 秒 | 需运行命令 + 等待 |
| 适用范围 | 任何元素 | 仅覆盖标准交互元素 |

详细的 DevTools 定位操作指南（包括自定义属性 `ng-click`、动态元素、表格单元格、深层嵌套等），请参见 **[Chrome DevTools 元素定位指南](docs/devtools-guide.md)**。

### 5.2 Auto 模式：自动下载

确认配置填写正确后，运行:

```bash
python3 main.py --mode auto
```

Auto 模式执行 `config.yaml` 中定义的 STEPS 步骤序列。支持重试机制 (默认最多 `MAX_RETRIES` 次)。

执行结果保存在 `OUTPUT_DIR` 目录:

- `latest_result.json`：最新结果 JSON
- `history.json`：历史记录 (累积)
- `latest_report.txt`：文本格式报告
- `result_YYYYMMDD_HHMMSS.png`：结果页面截图

如果 STEPS 未配置, 程序报错终止。请先在 config.yaml 中填写 STEPS 步骤序列 (详见 [第 6 章](#6-自定义步骤流程-steps))。

### 5.3 Cron 模式：定时任务

每天固定时间执行下载任务:

```bash
python3 main.py --mode cron
```

输出示例:

```
============================================================
  Schedule 模式：设置定时任务
============================================================

执行时间: 每天 09:00
执行命令: 30 9 * * * cd /path/to/chrome-auto-fetch && python3 main.py --mode auto >> ~/chrome-devtools-downloads/auto_download.log 2>&1

请将以下行添加到 crontab:
----------------------------------------
30 9 * * * cd /path/to/chrome-auto-fetch && python3 main.py --mode auto >> ~/chrome-devtools-downloads/auto_download.log 2>&1
----------------------------------------

添加方法:
  1. 运行: crontab -e
  2. 将上面的行粘贴到文件末尾
  3. 保存退出

验证:
  crontab -l  # 查看已添加的定时任务
```

**macOS 特别提醒:**

如果 cron 定时任务不执行，很可能是权限问题。macOS 需要给 cron 授予辅助功能权限:

1. 打开 **系统设置 → 隐私与安全性 → 辅助功能**
2. 点击 "+" 号
3. 按 `Command+Shift+G`，输入 `/usr/sbin/cron`
4. 添加并勾选

**Windows 替代方案:**

Windows 没有 cron，可以用 **任务计划程序 (Task Scheduler)**:

1. 按 `Win + R`，输入 `taskschd.msc`，回车
2. 点击右侧 "创建基本任务..."
3. 名称: `chrome-auto-fetch`
4. 触发器: "每天"，设置时间
5. 操作: "启动程序"
6. 程序或脚本: `C:\path\to\python.exe`
7. 添加参数: `C:\path\to\chrome-auto-fetch\main.py --mode auto`
8. 起始于: `C:\path\to\chrome-auto-fetch`
9. 完成

或者用 Windows 版的 cron 工具 (如 [schtasks 命令](https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/schtasks)):

```bat
schtasks /create /tn "chrome-auto-fetch" /tr "python C:\path\to\chrome-auto-fetch\main.py --mode auto" /sc daily /st 09:00
```

### 5.4 Daemon 模式：守护进程

不想配置系统定时任务? 可以用 Python 内置的调度器:

```bash
# 确保已安装 schedule
pip3 install schedule

# 启动守护进程 (会一直运行)
python3 main.py --mode daemon
```

Daemon 模式会一直在前台运行，到设定的时间 (`SCHEDULE_TIME`) 自动执行。按 `Ctrl+C` 停止。

这个模式适合:

- 在服务器上用 `nohup` 或 `systemd` 管理
- 测试定时任务是否正常
- 不想碰 cron 配置的情况

### 5.5 自定义配置文件路径

默认配置路径是 `config/config.yaml`。你也可以指定其他路径:

```bash
python3 main.py --config /path/to/custom-config.yaml --mode auto
```

这在你需要为不同网站维护多份配置时很有用。

---

## 6. 自定义步骤流程 (STEPS)

### 6.1 为什么需要 STEPS

旧版 Auto 模式是一个固定的 9 步管道: 导航→填参数→点搜索→等结果→点第一个→等弹窗→提取→关弹窗→保存。这对简单的"搜索→弹窗→下载链接"场景够用，但遇到以下情况就无法应对:

- 点击按钮后没有弹窗，而是直接下载或页面跳转
- 需要循环检查某个状态 (如进度条 100%)
- 需要多次等待不同条件 (先等元素出现，再等 URL 变化)
- 需要在不同时机提取变量供后续步骤使用
- 某个步骤可能失败但不应该终止整个流程
- 需要根据页面状态或变量值走不同流程 (条件分支)

**STEPS 配置**让你自由编排步骤序列，完全自定义搜索后的操作流程。支持 16 种动作类型 (含条件分支跳转 `branch`)，以及 MAX_STEPS / MAX_EXECUTIONS 安全限制防止配置过长和无限循环。

### 6.2 STEPS 必填

STEPS 是核心配置 — 不配 STEPS 时程序报错终止。你需要根据 discovery 模式的输出, 编写自己的步骤序列。

典型的 STEPS 流程:
1. `navigate` → 打开目标页面
2. `fill` → 填入搜索参数
3. `click` → 点击搜索按钮
4. `wait` → 等待结果加载
5. `click` → 点击搜索结果
6. `wait` → 等待弹窗/下载面板
7. `extract` → 提取下载链接
8. `save` → 保存结果

### 6.3 STEPS 配置格式

```yaml
STEPS:
  - action: navigate
    url: "https://example.com/search"
  - action: fill
    params:
      "#model": "Mate60 Pro"
      "#version": "HarmonyOS 4.0"
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
    selector: ".download-panel"
  - action: extract
    strategy: css
    selector: ".download-panel .download-btn"
    save_to: "download_urls"
  - action: save
```

每个步骤包含:
- **action** (必填): 动作类型，见下表
- 其他参数取决于 action 类型

### 6.4 支持的 Action 类型

| Action | 说明 | 主要参数 |
|---|---|---|
| `navigate` | 导航到 URL | `url` |
| `fill` | 填入输入框/下拉框 | `params: {selector: content}` 或 `selector + content`, 或 `match + value + content` |
| `click` | 点击元素 | `selector`, `index: 1/"last"/N`, 或 `match + value` (详见第 7 章) |
| `click_at` | 按坐标点击 | `x, y` |
| `type_text` | 键盘输入文本 | `text`, `submit_key?: str` (Enter 等) |
| `press_key` | 按键 | `key` (Escape, Enter, Tab...) |
| `wait` | 等待条件 (5 种策略) | `strategy`, `value/selector/expr`, `timeout` |
| `evaluate` | 执行 JS 表达式 | `expr`, `save_to?: 变量名` |
| `extract` | 提取下载链接 | `strategy: css/js/semantic/auto`, `selector/expr` |
| `loop` | 循环检查直到条件满足, 支持每轮执行子步骤 (`each`) | `condition`, `expr/selector/value`, `each?`, `max_iterations`, `interval`, `on_timeout` |
| `branch` | 条件分支跳转 (if-elif-else) | `branches`: [{if:JS, then:目标}, {elif:JS, then:目标}, {else:目标}] |
| `screenshot` | 截图 | `output?: 路径` |
| `snapshot` | 获取 Accessibility Tree | `format?: "text"/"json"`, `save_to?` |
| `new_page` | 打开新 tab | `url` |
| `list_pages` | 列出所有 tab | — |
| `save` | 保存结果到文件 | — |

每种 Action 的详细参数说明、用法示例和注意事项, 请参见 **[Action 类型详解](docs/actions.md)**。

### 6.5 通用参数

以下参数适用于所有 action 类型:

| 参数 | 类型 | 说明 |
|---|---|---|
| `name` | string | 步骤标签, 用于日志标识 (`Step 1/label: action`) 和 branch 跳转引用 |
| `delay` | number | 步骤执行后的等待秒数。默认取决于 action 类型 (大部分使用 `STEP_DELAY` 2s) |
| `on_fail` | string | 步骤失败时的处理策略: `abort` (终止流程, 默认), `skip` (跳过继续), `retry(N)` (重试 N 次, 当前版本等同 abort) |
| `${变量名}` | — | 所有 string 参数均支持变量引用, 在执行前被替换为实际值 |

`name` 让步骤日志更可读, 同时允许 `branch` 的 `then`/`else` 使用标签名代替数字步号, 维护更方便。

`delay` 覆盖全局 `STEP_DELAY`, 只影响当前步骤。适合在需要更长等待的步骤后使用 (如页面加载慢时增大 navigate 后的 delay)。

`on_fail` 提供步骤级容错, 适用于可能失败但不应该终止整个流程的步骤 (如关弹窗按钮可能不存在)。完整的 on_fail 说明见 [Action 类型详解](docs/actions.md) "附录: 通用参数" 部分。

### 6.6 变量提取与跨步骤传递

`evaluate` 和 `extract` 步骤支持 `save_to`，将结果存入变量。后续步骤用 `${变量名}` 引用:

```yaml
# 提取下载链接存到变量
- action: extract
  strategy: js
  expr: "document.querySelector('.download-btn').href"
  save_to: "download_url"

# 后续步骤引用变量
- action: evaluate
  expr: "console.log('${download_url}')"
```

变量在整个步骤流程中持久存在，任何步骤的 `save_to` 写入的变量都可以被后续步骤引用。

变量与条件分支 (`branch`) 配合使用的示例见 [Action 类型详解: branch](docs/actions.md#branch)。

### 6.7 步骤数量安全限制

为了防止配置过长或 branch 条件跳转导致的无限循环, 引入两个安全限制:

| 限制 | 作用 | 默认值 | 硬上限 |
|---|---|---|---|
| `MAX_STEPS` | 限制 STEPS 配置中定义的步骤数量上限 | 100 | 200 |
| `MAX_EXECUTIONS` | 限制运行时总执行次数 (含 branch 跳转的回溯) | 500 | 1000 |

`MAX_STEPS` 在步骤引擎启动时检测, 超限立即终止。`MAX_EXECUTIONS` 在每次步骤执行后计数, 超限时终止并保存已有部分结果。

配置示例:

```yaml
# 如果流程超过 100 步, 可调大 MAX_STEPS (但不超过 200)
MAX_STEPS: 150
# 如果 branch 流程需要较多重复执行, 可调大 MAX_EXECUTIONS (但不超过 1000)
MAX_EXECUTIONS: 800
```

各 Action 的完整参数表、进阶用法和注意事项，请参见 **[Action 类型详解文档](docs/actions.md)**。

---

## 7. 元素定位方式 ⭐️

chrome-auto-fetch 通过「选择器」定位页面上的元素 (输入框、按钮、链接等)。Discovery 模式会为每个元素生成多个候选选择器, 你需要从中挑选一个唯一的、稳定的写进 STEPS 配置。

目前支持 **2 种定位方式**, 可以根据场景灵活选用:

### 7.1 方式一: CSS 选择器 (`selector`)

最常见的定位方式, 使用标准 CSS 选择器语法直接匹配 DOM 元素。**不熟悉 CSS 选择器的用户, 请先阅读 [选择器入门指南](docs/selector-guide.md)。**

```yaml
- action: click
  selector: "#search-btn"

- action: fill
  params:
    "#golbalSearch": "OpenHarmony"
```

Discovery 模式会为每个元素生成多种 CSS 选择器候选, 按唯一性优先级排序:

| 优先级 | 选择器类型 | 示例 | 唯一性 |
|---|---|---|---|
| 1 | ID 选择器 | `#golbalSearch` | 100% 唯一 |
| 2 | 属性选择器 (href) | `a[href="/openharmony"]` | 链接通常唯一 |
| 3 | 属性选择器 (aria-label) | `[aria-label="搜索"]` | 通常唯一 |
| 4 | 属性选择器 (name) | `input[name="query"]` | 通常唯一 |
| 5 | 属性选择器 (placeholder) | `input[placeholder="搜索项目"]` | 通常唯一 |
| 6 | 组合 class 选择器 | `button.search-btn.primary` | 可能唯一 |
| 7 | 单 class 选择器 | `a.g-link` | 可能非唯一 |
| 8 | nth-child 路径 | `div > button:nth-of-type(2)` | 兜底 |

Discovery 输出中使用 ★ 标记已验证唯一的选择器, ○ 标记非唯一选择器:

```
[link] 鸿蒙开发工具广场/OpenHarmony字节码分析工具
  ★ a[href="https://gitcode.com/openharmony"]   (唯一 ✓)     ← 优先用这个
  ○ a.search-harmony-card-title                  (匹配3个)
  ○ a.g-link                                     (匹配4个)
```

**适用场景**: 大多数情况, 特别是目标元素有唯一 id 或 href 时。

**注意事项**:
- CSS 选择器无法按「可见文本内容」匹配 (CSS 没有 `:text()` 伪类)
- 页面结构变化时, nth-child 路径和 class 选择器可能失效
- 属性选择器中的值使用 HTML 原始属性值 (相对 href 而非绝对 URL)

### 7.2 方式二: 属性匹配 (`match`)

用 `match` 参数定位元素。`text` 是 `match` 的一种类型, 与 href、aria-label、name、placeholder 统属同一体系, 使用相同的 `match` + `value` 语法, 只是底层实现不同 — 属性类型转为 CSS 属性选择器, text 类型转为 JS 动态搜索。

与方式一相比, `match` 不需要写选择器层级路径 (如 `div > button:nth-of-type(2)`), 只关注属性值本身, 更**稳定抗页面结构变化。**

#### 7.2.1 属性类型匹配 — href / aria-label / name / placeholder

属性类型匹配将 match 参数转为 CSS 属性选择器, chrome CLI 的 click/fill 操作可直接使用, 无需额外 JS 评估:

```yaml
# 按 href 精确匹配链接
- action: click
  match: href
  value: "https://gitcode.com/openharmony"

# 按 href 部分匹配 (更灵活, 不需要写完整 URL)
- action: click
  match: href
  value: "openharmony"
  match_mode: contains

# 按 aria-label 匹配搜索按钮
- action: click
  match: aria_label
  value: "搜索"

# 按 name 属性匹配输入框
- action: fill
  match: name
  value: "query"
  content: "OpenHarmony"

# 按 placeholder 匹配输入框
- action: fill
  match: placeholder
  value: "搜索项目"
  content: "OpenHarmony"
```

**适用场景**:
- 同类元素很多 (如搜索结果列表中的多个链接), 用 href 精确定位特定一个
- 页面结构经常变化 (class 名、层级可能改动), 用不变的属性值定位更稳定
- 需要按属性值而非 CSS 选择器路径定位的场景

#### 7.2.2 文本匹配 (`match: text`) ⭐️

文本匹配是 `match` 的一种类型, 用于定位没有独特属性、只能通过可见文字区分的元素。CSS 选择器无法按文本内容匹配 (没有 `:text()` 伪类), `match: text` 通过 JS 在页面上动态遍历搜索来弥补这一能力缺口。

它与 href/aria-label/name/placeholder 一样属于 match 参数体系, 只是底层实现不同, 使用方式完全一致。

```yaml
# 点击"登录"按钮
- action: click
  match: text
  value: "登录"

# 点击包含"OpenHarmony"文字的链接
- action: click
  match: text
  value: "OpenHarmony"

# 点击文本完全等于"搜索"的元素 (严格模式)
- action: click
  match: text
  value: "搜索"
  match_mode: exact

# 填入文本为"搜索项目"的输入框
- action: fill
  match: text
  value: "搜索项目"
  content: "OpenHarmony"
```

**`match_mode` 对文本匹配的影响**:

- 默认 (`contains`): **匹配第一个 `.includes(value)` 为 true 的元素**, 即文本**包含**指定字符串即可命中
- `exact`: 匹配 `.textContent.trim() === value` 的元素, 即文本必须**完全等于**指定字符串才命中

**缩小搜索范围 — `tag` 参数**:

当多个元素包含相同文本时, 默认匹配第一个。可通过 `tag` 参数限定搜索范围, 只在指定标签中查找:

```yaml
# 只在 <a> 标签中搜索文本 (缩小范围)
- action: click
  match: text
  value: "OpenHarmony"
  tag: "a"

# 只在 <button> 标签中搜索文本
- action: click
  match: text
  value: "登录"
  tag: "button"
```

**适用场景**:
- 普通按钮 (如 "登录"、"注册"、"搜索")
- 菜单项、导航链接等纯文本元素
- 无 id、无 name、无独特 class 的场景, 只能通过文字区分元素
- 同页面多个元素包含相同文字时, 配合 `tag` 限定搜索范围

**注意事项**:
- 文本匹配通过 JS 在页面上遍历元素执行, 比纯 CSS 选择器稍慢
- `.includes()` 模式可能误匹配 (如搜索 "搜索" 可能同时匹配 "高级搜索" 按钮)
- 多个元素文本完全相同时, 默认匹配第一个; 如需精确区分, 优先用 `match: href` 或组合 `tag` 参数

#### 7.2.3 match 参数通用规则

支持的 `match` 类型:

| match 值 | 说明 | 底层实现 |
|---|---|---|
| `href` | 链接目标地址 | 转为 CSS 属性选择器: `a[href='...']` |
| `aria_label` (或 `aria-label`) | 无障碍标签 | 转为 CSS 属性选择器: `[aria-label='...']` |
| `name` | 表单元素 name 属性 | 转为 CSS 属性选择器: `[name='...']` |
| `placeholder` | 输入框占位文本 | 转为 CSS 属性选择器: `[placeholder='...']` |
| `text` | 元素可见文本内容 | JS 动态遍历搜索 (CSS 无法按文本匹配) |

`match_mode` 参数控制匹配精度, 对所有 match 类型均有效:

| match_mode | 说明 | 对属性类型的效果 | 对 text 的效果 |
|---|---|---|---|
| `exact` (默认) | 值完全匹配 | `a[href='完整值']` | `.textContent.trim() === '值'` |
| `contains` | 值包含指定字符串 | `a[href*='部分值']` | `.textContent.includes('值')` |

通用规则:
- `match` 和 `selector` 同时存在时, `match` 优先 (selector 被忽略)
- `fill` 使用 `match` 时, `value` 是匹配搜索值, `content` 是实际填入值; `content` 为必填参数
- `match: href` 的 `value` 使用 HTML 原始 href 属性值 (可能是相对路径如 `/openharmony`, 而非浏览器解析后的绝对 URL)

### 7.3 两种方式选择指南

| 场景 | 推荐方式 | 示例 |
|---|---|---|
| 元素有唯一 id | 方式一: `selector` | `selector: "#golbalSearch"` |
| 链接需要精确点击 | 方式二: `match: href` | `match: href, value: "/openharmony"` |
| 输入框有 placeholder | 方式一 或 方式二 | `selector: "input[placeholder='搜索项目']"` 或 `match: placeholder` |
| 同 class 多按钮 | 方式二: `match: text` | `match: text, value: "登录"` |
| 页面结构常变化 | 方式二 (属性值更稳定) | `match: href, value: "openharmony", match_mode: contains` |
| 搜索结果列表项 | 方式二: `match: href` | `match: href, value: "kernel_linux_6.6"` |

**原则**: 优先用唯一性最高的定位方式 (id > href > aria-label > text), 确保自动化流程的稳定性。

---

## 8. 项目结构

```
chrome-auto-fetch/
│
├── main.py                      # CLI 入口, 参数解析, 模式分发
├── pyproject.toml               # Python 项目元数据
├── requirements.txt             # Python 依赖
├── .gitignore                   # Git 忽略规则
├── README.md                    # 本文档
│
├── config/
│   ├── config.example.yaml      # 配置示例 (含中文注释)
│   └── config.yaml              # 用户配置 (gitignore 排除, 需手动创建)
│
├── scripts/
│   ├── start-chrome-debug.sh        # macOS Chrome 启动脚本
│   ├── start-chrome-debug-linux.sh  # Linux Chrome 启动脚本
│   └── start-chrome-debug.bat       # Windows Chrome 启动脚本
│
├── src/
│   ├── __init__.py              # 包导出
│   ├── connection.py            # Chrome 连接发现 (3 层策略)
│   ├── chrome_cli.py            # chrome-devtools CLI 封装类
│   ├── discover.py              # Discovery 模式 (页面结构分析)
│   ├── step_engine.py           # 步骤引擎 (可编排动作序列 + branch 条件跳转 + 安全限制)
│   ├── result.py                # 结果保存 (JSON / 历史 / 文本报告)
│   └── scheduler.py             # 定时调度 (cron 生成 + daemon 守护)
│
└── chrome-debug-profile/        # Chrome 独立 profile (gitignore 排除)
```

---

## 9. 下载地址提取方式

STEPS 中的 `extract` 步骤通过 `strategy` 参数选择提取方式:

### 方式 1: CSS 选择器直接提取 (优先级最高)

如果下载弹窗中有 `<a href="...">` 这样的直接链接，使用 `strategy: css` 配合 `selector`:

```yaml
- action: extract
  strategy: css
  selector: ".modal .download-btn"
```

工具会在页面中执行 JavaScript，用 `document.querySelectorAll` 找到匹配的元素，提取所有 `href` 属性。

**适用场景:** 下载链接是直接写在 HTML 中的静态 `<a>` 标签。

### 方式 2: JS 表达式提取 (优先级次之)

如果下载地址是通过 JavaScript 动态生成的，或者不在 `href` 属性里，使用 `strategy: js` 配合 `expr`:

```yaml
- action: extract
  strategy: js
  expr: "document.querySelector('.download-item').getAttribute('data-url')"

- action: extract
  strategy: js
  expr: "getDownloadLink()"

- action: extract
  strategy: js
  expr: "window.__config__.downloadUrl"
```

工具会通过 CDP 的 `Runtime.evaluate` 执行你的 JS 表达式，取返回值作为下载地址。

**适用场景:** 下载地址在 JavaScript 变量中、通过 AJAX 获取、或放在自定义 data 属性中。

### 方式 3: 语义搜索自动提取 (兜底策略)

使用 `strategy: semantic` 或 `strategy: auto` 让工具自动尝试:

```yaml
- action: extract
  strategy: auto
```

自动策略会依次尝试:

1. CSS 选择器提取 `<a>` href
2. JS 表达式提取 URL
3. 语义搜索: 对页面文本进行正则匹配，搜索包含 "download" 的 URL
4. 通过 Accessibility Tree 查找包含 "下载" 或 "download" 关键词的元素
5. 查找附近包含 "下载"/"download" 文本的 `<a>` 链接

这种方式不精确，但无需配置具体选择器。适合快速测试。

**适用场景:** 你不确定下载地址在页面上怎么呈现，或者只是想试试能不能抓到。

### 提取优先级总结

```
STEPS 中 extract 步骤的 strategy 参数决定提取方式:
  strategy: css  → 使用 CSS 选择器提取 <a> href
  strategy: js   → 使用 JS 表达式提取 URL
  strategy: auto → 先尝试 CSS, 再尝试 JS, 最后语义搜索
```

---

## 10. 常见问题 (FAQ)

### Q1: Chrome 的"审批弹窗"怎么关闭?

**问题:** 启动 Debug Chrome 后，每次自动化操作时，Chrome 顶部会出现 "Chrome 正被自动测试软件控制" 的黄色提示条。

**答案:** 这个提示条无法通过任何方式关闭。它是 Chrome 安全机制的一部分，当检测到 `--remote-debugging-port` 时自动弹出。好消息是它不影响自动化流程的正常运行：工具依然可以正常导航、点击、提取数据。忽略它即可。

### Q2: macOS 上两个 Chrome 无法并存?

**问题:** 我在 macOS 上运行启动脚本，结果它把我日常用的 Chrome 页面打开了，而不是启动一个新的 Chrome 实例。

**答案:** macOS 上直接调用 `/Applications/Google Chrome.app/Contents/MacOS/Google Chrome` 会复用到已有的 Chrome 进程。**必须使用 `open -na` 命令**:

```bash
# 正确: 强制新建实例
open -na "Google Chrome" --args --remote-debugging-port=9333 --user-data-dir="$HOME/chrome-debug-profile" --no-first-run
```

`-n` 参数的意思是 "新建实例 (New instance)"，`-a` 表示 "打开指定应用 (Application)"。项目自带的 `scripts/start-chrome-debug.sh` 已经正确处理了这一点。

### Q3: DevToolsActivePort 文件找不到?

**问题:** Chrome 启动后，程序报错说找不到 DevToolsActivePort 文件。

**答案:** DevToolsActivePort 文件在 Chrome 成功启动并初始化远程调试端口后才会生成，通常在 profile 目录下 (`~/chrome-debug-profile/DevToolsActivePort`)。排查步骤:

1. 确认 Chrome 确实在端口 9333 上运行:
   ```bash
   curl -s http://127.0.0.1:9333/json/version
   ```
   如果返回 JSON 数据，说明 Chrome 已启动。如果连接失败，Chrome 没起来。

2. 检查 profile 目录是否存在:
   ```bash
   ls ~/chrome-debug-profile/
   ```
   如果目录是空的，说明 Chrome 没有使用这个 profile。检查启动参数中的 `--user-data-dir` 路径是否正确。

3. 如果 Chrome 已启动但端口不是 9333 (例如启用了 9222):
   - 检查是否未使用 `open -na` (macOS)
   - 检查是否已有 Chrome 占用了目标端口

   实际上，这个错误很少出现。因为程序的连接策略有 3 层兜底:

- 如果 DevToolsActivePort 不存在，会自动尝试 HTTP 发现 (`/json/version`)
- 如果 HTTP 发现也失败，才报连接错误

### Q4: 定时脚本执行时 Chrome 关闭了?

**问题:** 我用 cron 设置了每天早上 9 点执行，但到点发现脚本报错说连不上 Chrome。

**答案:** cron 任务运行在一个全新的 shell 环境中，没有图形界面。如果 Debug Chrome 没有提前启动，cron 任务连不上 Chrome 就会失败。

**解决方案:**

1. **Debug Chrome 保持运行:** 确认 Debug Chrome 一直在运行。如果你的系统会重启，需要在重启后重新启动 Debug Chrome。可以添加开机自启:
   - macOS: 在 "系统设置 → 通用 → 登录项" 中添加启动脚本
   - Linux: 创建 systemd service 或添加到 `/etc/rc.local`
   - Windows: 创建计划任务在开机时启动

2. **或者用 daemon 模式:** `python3 main.py --mode daemon` 会一直停留在前台，你可以用 `nohup`、`screen`、`tmux` 或 systemd 来管理:

   ```bash
   # Linux/macOS 用 nohup 后台运行
   nohup python3 main.py --mode daemon > /dev/null 2>&1 &

   # 用 systemd (Linux) 管理
   # 创建 /etc/systemd/system/chrome-auto-fetch.service
   ```

3. **或者在脚本中自动检查 Chrome 状态:** 编写一个包装脚本，先检查 Chrome 是否在运行，如果不在就先启动再执行自动化:

   ```bash
   #!/bin/bash
   # 检查 Chrome 是否在运行
   if ! curl -s http://127.0.0.1:9333/json/version > /dev/null 2>&1; then
       # 启动 Chrome
       open -na "Google Chrome" --args --remote-debugging-port=9333 \
           --user-data-dir="$HOME/chrome-debug-profile" --no-first-run
       sleep 5  # 等待启动
   fi
   # 执行自动化
   cd /path/to/chrome-auto-fetch && python3 main.py --mode auto
   ```

### Q5: Windows 下 chrome-devtools 编译失败?

**问题:** 在 Windows 上运行 `cargo build --release` 时报错，提示找不到链接器 (linker) 或 C 编译器。

**答案:**

1. **安装 Visual Studio Build Tools:**
   - 下载 [Visual Studio 2022 Build Tools](https://visualstudio.microsoft.com/downloads/#build-tools-for-visual-studio-2022)
   - 运行安装程序
   - 在工作负载中选择 "Desktop development with C++" (使用 C++ 的桌面开发)
   - 在右侧详细信息中，确保选择:
     - MSVC v143 - VS 2022 C++ x64/x86 build tools
     - Windows 10/11 SDK
     - C++ CMake tools for Windows
   - 点击安装

2. **安装后重启终端:** 确保环境变量生效。

3. **使用 "Developer Command Prompt":**
   - 开始菜单搜索 "Developer Command Prompt for VS 2022"
   - 在这个终端中运行 `cargo build --release`

4. **仍然不行?** 尝试安装全量的 Visual Studio Community (免费版) 而非仅 Build Tools:
   - 下载 [Visual Studio Community](https://visualstudio.microsoft.com/vs/community/)
   - 安装时同样选择 "Desktop development with C++"

### Q6: GPU 进程崩溃?

**问题:** 启动 Debug Chrome 后，终端显示 "GPU process exited unexpectedly" 或类似错误。

**答案:** 这在无图形界面环境 (如 Linux 服务器) 或某些虚拟机中很常见。启动脚本已经加了 `--disable-gpu` 参数。如果仍然报错，可以额外添加:

```bash
# Linux 服务器推荐参数
google-chrome --remote-debugging-port=9333 \
    --user-data-dir="$HOME/chrome-debug-profile" \
    --no-first-run \
    --disable-gpu \
    --disable-software-rasterizer \
    --disable-dev-shm-usage \
    --no-sandbox \
    --headless &   # 如果不需要看界面, 加 headless 模式
```

各参数含义:

| 参数 | 作用 |
|---|---|
| `--disable-gpu` | 禁用 GPU 加速 |
| `--disable-software-rasterizer` | 禁用软件渲染 (有时 GPU 禁用后仍报错) |
| `--disable-dev-shm-usage` | 防止 /dev/shm 空间不足 (Docker 容器常见) |
| `--no-sandbox` | 禁用沙盒 (仅限信任的环境，有安全风险) |
| `--headless` | 无头模式，不显示界面 |

实际上，GPU 进程崩溃通常不会影响 CDP 自动化的正常运行。只要 Chrome 主进程还在，curl 能访问到 `/json/version`，自动化就可以正常工作。

---

## 11. 安全说明

### 9.1 远程调试端口安全

启用 `--remote-debugging-port` 会打开一个 HTTP 服务，默认只监听 `127.0.0.1` (本地回环地址)，所以只有你自己能访问。但请注意:

- **不要**将 Debug Chrome 暴露在公网上。任何人如果能访问到端口 9333，就可以通过 CDP 完全控制你的浏览器 (打开网页、读取数据、执行 JS)。
- 如果你需要在远程机器上使用，建议通过 SSH 隧道 (`ssh -L 9333:127.0.0.1:9333 user@remote`) 而非直接开放端口。

### 9.2 独立 profile

Debug Chrome 使用独立的用户数据目录 (默认 `~/chrome-debug-profile`)，与日常浏览的 profile 完全隔离。你在 Debug Chrome 中的登录状态、Cookie、浏览记录不会影响日常 Chrome。

### 9.3 敏感信息

配置文件中可能包含登录凭据 (如果网站需要填用户名密码)。建议:

- 不要将 `config.yaml` 提交到 Git (项目已通过 `.gitignore` 排除)
- 如果使用场景需要保存密码，考虑使用环境变量或加密存储

### 9.4 自动化风险

自动化操作可能触发目标网站的反爬机制或风控策略。请合理控制访问频率 (`STEP_DELAY` 字段可以控制操作间隔)，遵守目标网站的使用条款。

---

## 12. 许可证

本项目基于 MIT 许可证开源。

```
MIT License

Copyright (c) 2024 chrome-auto-fetch

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
