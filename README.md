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

## 3. 快速开始

环境就绪后, 3 步即可运行:

```bash
cp config/config.example.yaml config/config.yaml   # 创建配置
python3 main.py --mode discover                     # 探索页面结构
python3 main.py --mode auto                         # 执行自动化流程
```

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

### 5.1 Discovery 模式：探索页面结构⭐️

首次使用某个网站时，你并不知道页面元素对应的 CSS 选择器是什么。Discovery 模式帮你解决这个问题:

```bash
python3 main.py --mode discover
```

运行后，工具会:

1. 导航到目标网站 (`TARGET_URL`)
2. 输出页面的 Accessibility Tree (前 50 行)
3. 输出所有可交互元素列表 (input、select、button、textarea、a 标签)
4. 每个元素显示: tag、CSS selector、id、name、type、text
5. 保存页面截图到输出目录

根据输出，你可以找到输入框、搜索按钮、结果链接的 CSS 选择器，填入 STEPS 步骤序列中。

**使用流程:**

```
1. 在 config.yaml 中填写 TARGET_URL 和 CLI_PATH
2. 运行 python3 main.py --mode discover
3. 查看输出中的可交互元素列表
4. 根据输出编写 STEPS 步骤序列 (详见第 6 章)
5. 运行 python3 main.py --mode auto 开始下载
```

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
| `fill` | 填入输入框/下拉框 | `params: {selector: value}` 或 `selector + value` |
| `click` | 点击元素 | `selector`, `index: 1/"last"/N` (选第几个) |
| `click_at` | 按坐标点击 | `x, y` |
| `type_text` | 键盘输入文本 | `text`, `submit_key?: str` (Enter 等) |
| `press_key` | 按键 | `key` (Escape, Enter, Tab...) |
| `wait` | 等待条件 (5 种策略) | `strategy`, `value/selector/expr`, `timeout` |
| `evaluate` | 执行 JS 表达式 | `expr`, `save_to?: 变量名` |
| `extract` | 提取下载链接 | `strategy: css/js/semantic/auto`, `selector/expr` |
| `loop` | 循环检查直到条件满足 | `condition`, `expr/selector/value`, `max_iterations`, `interval`, `on_timeout` |
| `branch` | 条件分支跳转 (if-elif-else) | `branches`: [{if:JS, then:目标}, {elif:JS, then:目标}, {else:目标}] |
| `screenshot` | 截图 | `output?: 路径` |
| `snapshot` | 获取 Accessibility Tree | `format?: "text"/"json"`, `save_to?` |
| `new_page` | 打开新 tab | `url` |
| `list_pages` | 列出所有 tab | — |
| `save` | 保存结果到文件 | — |

### 6.5 Wait 的 5 种策略

| Strategy | 说明 | 参数 |
|---|---|---|
| `text` | 等指定文字出现 | `value: "搜索结果"` |
| `element` | 等 CSS 元素出现在 DOM 中 | `selector: ".download-panel"` |
| `url_change` | 等 URL 发生变化 (页面跳转) | `timeout` |
| `js` | 等 JS 表达式返回 truthy 值 | `expr: "document.querySelectorAll('.result').length > 0"` |
| `timeout` | 固定等待 N 毫秒 | `timeout: 3000` |

所有 wait 策略都支持 `timeout` 参数 (毫秒)，超时后步骤失败。

### 6.6 Loop 循环检查

适用于需要等待某个异步过程完成的场景 (如进度条、文件生成、异步下载):

```yaml
- action: loop
  condition: js
  expr: "document.querySelector('.progress').textContent.includes('100%')"
  max_iterations: 60
  interval: 2000
  on_timeout: fail
```

| 参数 | 说明 | 默认值 |
|---|---|---|
| `condition` | 检查类型: `js` / `element_exists` / `text_exists` | `js` |
| `expr` | JS 条件表达式 (condition=js 时) | — |
| `selector` | CSS 选择器 (condition=element_exists 时) | — |
| `value` | 文本内容 (condition=text_exists 时) | — |
| `max_iterations` | 最多循环次数 | 30 |
| `interval` | 每次检查间隔 (毫秒) | 2000 |
| `on_timeout` | 超时后行为: `fail` / `continue` / `extract_and_continue` | `fail` |

### 6.7 步骤级错误处理

每个步骤可以配置 `on_fail` 策略:

```yaml
- action: click
  selector: ".maybe-not-exist-btn"
  on_fail: skip
```

| on_fail | 行为 |
|---|---|
| `abort` | 整体流程终止 (默认) |
| `skip` | 跳过此步，继续下一步 |
| `retry(N)` | 重试 N 次 (当前版本等同 abort) |

### 6.8 变量提取与跨步骤传递

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

### 6.9 典型场景配置示例

#### 场景 A: 直接下载 (无弹窗)

点击下载按钮后直接触发下载，不需要弹窗:

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

#### 场景 B: 弹窗场景

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

#### 场景 C: 循环检查进度条

启动任务后循环检查直到进度完成:

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

#### 场景 D: 页面跳转 (点击后跳到下载页)

点击后网页跳转，在新页面提取下载链接:

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

#### 场景 E: 纯 STEPS 配置

只使用 STEPS 的完整配置示例:

```yaml
CLI_PATH: "/usr/local/bin/chrome-devtools"
WS_ENDPOINT: ""
OUTPUT_DIR: "~/chrome-devtools-downloads"
STEP_DELAY: 2
MAX_RETRIES: 3

STEPS:
  - action: navigate
    url: "https://example.com"
  - action: click
    selector: "#download-section"
  - action: wait
    strategy: element
    selector: "#file-list"
  - action: click
    selector: "#file-list .file-item:last-child .view-btn"
    index: "last"
  - action: wait
    strategy: element
    selector: ".detail-download-btn"
  - action: extract
    strategy: css
    selector: ".detail-download-btn"
    save_to: "download_urls"
  - action: save
```

#### 场景 F: 条件分支 — 根据页面状态跳转

点击搜索后, 根据页面状态决定走不同流程:

```yaml
STEPS:
  - action: navigate                              # Step 1
    url: "https://example.com/search"
    name: "open_search"
  - action: fill                                  # Step 2
    params: {"#model": "Mate60"}
    name: "fill_params"
  - action: click                                 # Step 3
    selector: "#search-btn"
    name: "search"
  - action: wait                                  # Step 4
    strategy: element
    selector: ".result-list"
    name: "wait_results"
  - action: branch                                # Step 5: if-elif-else
    branches:
      - if: "document.querySelector('.modal') !== null"
        then: "handle_popup"
      - elif: "document.querySelector('.direct-download') !== null"
        then: "direct_download"
      - else: "save_result"
  - action: wait                                  # Step 6
    strategy: element
    selector: ".modal .download-btn"
    name: "handle_popup"
  - action: extract                               # Step 7
    strategy: css
    selector: ".modal .download-btn"
    save_to: "download_urls"
  - action: click                                 # Step 8
    selector: ".modal .close-btn"
    on_fail: skip
  - action: extract                               # Step 9
    strategy: js
    expr: "document.querySelector('.direct-download').href"
    save_to: "download_urls"
    name: "direct_download"
  - action: save                                  # Step 10
    name: "save_result"
```

#### 场景 G: 条件分支 + 变量 — 根据提取到的值决定后续流程

先提取文件类型变量, 再根据变量值跳转到不同的下载流程:

```yaml
STEPS:
  - action: navigate                              # Step 1
    url: "https://example.com/files"
    name: "open_files"
  - action: extract                               # Step 2: 提取文件类型
    strategy: js
    expr: "document.querySelector('.file-type').textContent.trim()"
    save_to: "file_type"
    name: "detect_type"
  - action: branch                                # Step 3: if-elif-else
    branches:
      - if: "${file_type} === 'PDF'"
        then: "pdf_download"
      - elif: "${file_type} === 'ZIP'"
        then: "zip_download"
      - else: "generic_download"
  - action: click                                 # Step 4: PDF
    selector: ".pdf-download-btn"
    name: "pdf_download"
  - action: extract                               # Step 5
    strategy: css
    selector: ".pdf-download-btn"
    save_to: "download_urls"
  - action: click                                 # Step 6: ZIP
    selector: ".zip-download-btn"
    name: "zip_download"
  - action: extract                               # Step 7
    strategy: css
    selector: ".zip-download-btn"
    save_to: "download_urls"
  - action: extract                               # Step 8: 通用
    strategy: auto
    name: "generic_download"
  - action: save                                  # Step 9
    name: "save_result"
```

### 6.10 Branch 条件分支跳转

`branch` 动作提供 if-elif-else 条件跳转能力，让你根据页面状态或变量值决定后续执行哪一步。

#### 基本语法

```yaml
- action: branch
  branches:                       # 条件分支列表
    - if: "JS表达式1"             # if: 第一个条件
      then: 步号或标签             # if 满足时跳转的目标
    - elif: "JS表达式2"           # elif: 更多条件 (可选, 可多项)
      then: 步号或标签             # elif 满足时跳转的目标
    - else: 步号或标签             # else: 默认跳转 (可选, 值就是目标)
```

关键字对应 Python 的 if-elif-else: `branches` 列表中, `if` 是第一个条件, `elif` 是后续条件, `else` 是兜底跳转。`else` 的值直接是跳转目标, 不需要 `then` 关键字。

#### 工作原理

1. `branches` 列表按顺序评估每个条件
2. `if` 条件最先评估 (相当于 Python 的 if)
3. 若 `if` 为 truthy, 跳转到其 `then` 指定的步骤, 后续 `elif` 和 `else` 不再判断
4. 若 `if` 为 falsy, 依次评估 `elif` 条件 (相当于 elif)
5. 第一个 truthy 的 `elif` 条件触发跳转到其 `then` 步骤
6. 所有条件都不满足:
   - 有 `else` 项: 跳转到 `else` 值指定的步骤
   - 无 `else` 项: 继续执行下一个步骤 (正常顺序)
7. `then`/`else` 的目标可以使用数字步号 (1-based) 或步骤的 `name` 标签

#### 变量支持

`if`/`elif` 表达式支持 `${变量名}` 引用之前 `save_to` 存入的变量:

```yaml
- action: branch
  branches:
    - if: "${file_type} === 'PDF'"
      then: "pdf_download"
    - elif: "${file_type} === 'ZIP'"
      then: "zip_download"
    - else: "generic_download"
```

`${file_type}` 在执行前会被替换为变量的实际值 (如 `"PDF"`), 最终执行的 JS 表达式变为 `"PDF" === 'PDF'`, 返回 `true` 触发跳转。

#### 步骤标签 (name)

每个步骤可以添加 `name` 字段作为人类可读的标识符:

```yaml
- action: navigate
  url: "https://example.com/search"
  name: "open_search"
```

`name` 有两个用途:

1. **日志标识**: 执行日志会显示步骤标签, 如 `Step 1/open_search: navigate`, 更容易定位问题
2. **branch then/else 引用**: `then` 和 `else` 可以使用 `name` 值代替数字步号, 让配置更可读:

```yaml
- action: branch
  branches:
    - if: "document.querySelector('.modal') !== null"
      then: "handle_popup"    # 引用 name="handle_popup" 的步骤
    - else: "save_result"     # 引用 name="save_result" 的步骤
```

使用 `name` 引用时, 即使步骤顺序调整也不需要修改 then/else 值 — 更容易维护。

`name` 是可选的。没有 `name` 的步骤在日志中只显示数字编号, branch then/else 只能使用数字步号。

#### 参数说明

| 参数 | 说明 | 类型 | 必填 |
|---|---|---|---|
| `branches` | 条件分支列表, 每项含 if/elif/else 关键字 | list | 是 |
| `branches[].if` | 第一个条件表达式 (Python if) | string (JS) | 第一个必须有 |
| `branches[].elif` | 后续条件表达式 (Python elif) | string (JS) | 否 |
| `branches[].then` | if/elif 满足时跳转的目标步号或标签 | int/string | if/elif 项必须有 |
| `branches[].else` | 默认跳转目标 (Python else, 值即目标) | int/string | 否 |

#### 注意事项

- **步号/标签范围**: `then`/`else` 使用数字时必须在 1 ~ STEPS 总数范围内; 使用 name 标签时必须存在对应的步骤
- **branch 不触发 on_fail**: branch 总是返回 success=True, 无匹配条件是预期行为
- **步号对照**: 建议用 `name` 标签标注步骤, `then`/`else` 引用标签比数字步号更易维护

### 6.11 步骤数量安全限制

为了防止配置过长或 branch 条件跳转导致的无限循环, 引入两个安全限制:

#### MAX_STEPS (配置级限制)

限制 STEPS 配置中定义的步骤数量上限。

| 项目 | 值 |
|---|---|
| 默认值 | 100 |
| 硬上限 | 200 (即使配置超过 200, 也会被自动 clamp) |
| 检查时机 | 步骤引擎启动时 |
| 超限行为 | 立即终止, 状态为 `failed`, 错误信息包含实际步数和上限值 |

#### MAX_EXECUTIONS (运行时限制)

限制步骤引擎运行时总执行次数 (包含重复执行, 如 branch 跳转导致的回溯)。

| 项目 | 值 |
|---|---|
| 默认值 | 500 |
| 硬上限 | 1000 |
| 检查时机 | 每次步骤执行后 |
| 超限行为 | 终止执行, 状态为 `failed`, 保存已有部分结果 |

#### 为什么需要这两个限制?

- **MAX_STEPS**: 防止用户定义过长的步骤序列 (比如 500 步), 导致配置难以维护和调试
- **MAX_EXECUTIONS**: 防止 branch 条件跳转导致的无限循环。例如: Step 3 branch → goto 2, Step 2 branch → goto 3, 形成循环。每次步骤执行都会计数, 超过上限后自动终止并保存已有结果

#### 配置示例

```yaml
# 如果你的流程超过 100 步, 可以调大 MAX_STEPS (但不超过 200)
MAX_STEPS: 150

# 如果你的 branch 流程需要较多重复执行, 可以调大 MAX_EXECUTIONS (但不超过 1000)
MAX_EXECUTIONS: 800
```

---

## 7. 项目结构

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

## 8. 下载地址提取方式

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

## 9. 常见问题 (FAQ)

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

## 10. 安全说明

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

## 11. 许可证

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
