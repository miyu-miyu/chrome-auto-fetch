# 前置条件与安装指南

本文档详细说明了 chrome-auto-fetch 的前置条件与安装步骤。如果你已有环境，可以直接回到 [主文档](../README.md) 继续。

---

## 前置条件

### Python 3.6+

**macOS:**

```bash
# Homebrew
brew install python3

# 或从 python.org 下载安装包
# https://www.python.org/downloads/
```

验证: `python3 --version`

**Linux:**

```bash
# Debian/Ubuntu
sudo apt install python3 python3-pip

# CentOS/RHEL 7
sudo yum install python3 python3-pip

# CentOS/RHEL 8 / Fedora
sudo dnf install python3 python3-pip

# Arch Linux
sudo pacman -S python python-pip

# Alpine
apk add python3 py3-pip
```

如果没有包管理器 (如离线服务器、最小化安装):

1. 从 [python.org](https://www.python.org/downloads/source/) 下载源码包
2. 编译安装: `./configure && make && sudo make install`
3. 或下载预编译二进制: [conda/miniconda](https://docs.conda.io/en/latest/miniconda.html) (无需 root)

验证: `python3 --version`

**Windows:**

```powershell
# winget (Windows 10 1709+ 内置)
winget install Python.Python.3

# 或从 python.org 下载安装包
# https://www.python.org/downloads/
# 安装时务必勾选 "Add Python to PATH"

# 或从 Microsoft Store 搜索 "Python" 安装
```

验证: `python --version`

注意: Windows 上 Python 命令通常是 `python` 而非 `python3`，本文档统一用 `python3`，Windows 用户请替换为 `python`。

### Rust 工具链 (编译 chrome-devtools-cli)

chrome-auto-fetch 依赖 [chrome-devtools-cli](https://github.com/aeroxy/chrome-devtools-cli) 这个 Rust 项目。你需要先安装 Rust 工具链才能编译它。

**macOS:**

```bash
# Homebrew
brew install rust

# 或 rustup (推荐, 版本最新)
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
```

**Linux:**

```bash
# rustup (推荐, 所有发行版通用)
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
# 安装后重启终端, 或执行: source $HOME/.cargo/env

# 包管理器安装 (版本可能较旧, 不推荐):
# Debian/Ubuntu:
sudo apt install rustc cargo
# CentOS/RHEL 7:
sudo yum install rust cargo
# CentOS/RHEL 8 / Fedora:
sudo dnf install rust cargo
# Arch Linux:
sudo pacman -S rustup
```

如果没有网络 (离线环境):

1. 从 [rustup.rs](https://rustup.rs/) 下载 `rustup-init` 安装脚本/二进制
2. 传到目标机器执行: `sh rustup-init.sh` (Linux) 或 `rustup-init.exe` (Windows)
3. 或从 [rust-lang.org](https://www.rust-lang.org/tools/install) 下载离线安装包

**Windows:**

```powershell
# winget
winget install Rustlang.Rustup

# 或从 rustup.rs 下载 rustup-init.exe 运行
# https://rustup.rs/

# 或从 Microsoft Store 搜索 "Rust" 安装
```

安装后验证:

```bash
rustc --version
cargo --version
```

**Windows 特别注意:** Rust 编译需要 Visual Studio C++ Build Tools。安装 rustup-init.exe 时，它会有提示安装 Visual Studio Build Tools。你也可以手动安装:

1. 下载 [Visual Studio 2022 Build Tools](https://visualstudio.microsoft.com/downloads/#build-tools-for-visual-studio-2022)
2. 运行安装程序，勾选 "Desktop development with C++" (使用 C++ 的桌面开发)
3. 确保 "Windows 10/11 SDK" 也被选中

### Chrome / Chromium 浏览器

**macOS:**

```bash
# Homebrew
brew install --cask google-chrome

# 或从 google.com/chrome 下载安装包
# https://www.google.com/chrome/
```

**Linux:**

```bash
# Debian/Ubuntu (需先添加 Google 仓库)
wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | sudo apt-key add -
sudo apt update
sudo apt install google-chrome-stable

# CentOS/RHEL 7
sudo yum install https://dl.google.com/linux/direct/google-chrome-stable_current_x86_64.rpm

# CentOS/RHEL 8 / Fedora
sudo dnf install https://dl.google.com/linux/direct/google-chrome-stable_current_x86_64.rpm

# Arch Linux (AUR)
sudo pacman -S google-chrome    # 或 chromium

# 或用 Chromium (开源版, 大部分 Linux 仓库自带):
# Debian/Ubuntu: sudo apt install chromium-browser
# CentOS/RHEL:   sudo yum install chromium
# Fedora:        sudo dnf install chromium
# Arch:          sudo pacman -S chromium
```

没有包管理器 (离线环境): 从 [google.com/chrome](https://www.google.com/chrome/) 下载 .deb 或 .rpm 包, 传到目标机器安装:

```bash
# Debian/Ubuntu 系
sudo dpkg -i google-chrome-stable_current_amd64.deb

# CentOS/RHEL/Fedora 系
sudo rpm -i google-chrome-stable_current_x86_64.rpm
```

**Windows:**

```powershell
# winget
winget install Google.Chrome

# 或从 google.com/chrome 下载安装包
# https://www.google.com/chrome/

# 或从 Microsoft Store 搜索 "Google Chrome" 安装
```

没有 winget (旧版 Windows): 从 [google.com/chrome](https://www.google.com/chrome/) 下载离线安装包 (点击页面上的 "其他平台" → "Windows 64-bit 离线安装程序")。

### Git

**macOS:**

```bash
# Homebrew
brew install git

# 或安装 Xcode Command Line Tools (包含 git)
xcode-select --install
```

**Linux:**

```bash
# Debian/Ubuntu
sudo apt install git

# CentOS/RHEL 7
sudo yum install git

# CentOS/RHEL 8 / Fedora
sudo dnf install git

# Arch Linux
sudo pacman -S git

# Alpine
apk add git
```

没有包管理器: 从 [git-scm.com](https://git-scm.com/) 下载源码编译, 或下载预编译二进制包。

**Windows:**

```powershell
# winget
winget install Git.Git

# 或从 git-scm.com 下载安装包
# https://git-scm.com/

# 或从 Microsoft Store 搜索 "Git" 安装
```

没有 winget: 从 [git-scm.com](https://git-scm.com/) 下载 32-bit 或 64-bit 安装包 (便携版 PortableGit 也可用, 无需安装)。

### Python 依赖

核心依赖只有 pyyaml (>=5.1)。Daemon 模式额外需要 schedule 库。

```bash
# 基础安装 (必需)
pip3 install pyyaml>=5.1

# 如果用 daemon 模式 (可选)
pip3 install schedule>=1.1.0
```

---

## 安装步骤

### 克隆项目

```bash
git clone https://github.com/your-username/chrome-auto-fetch.git
cd chrome-auto-fetch
```

### 安装 Python 依赖

```bash
pip3 install -r requirements.txt
```

`requirements.txt` 内容:

```
pyyaml>=5.1
schedule>=1.1.0  # optional: needed for daemon mode only
```

pyyaml 是必须的：没有它程序无法读取 YAML 配置文件。schedule 仅在 daemon 模式下需要，cron 模式不需要。

如果你只需要基础功能 (discovery / auto / cron 模式)，只装 pyyaml 就够了:

```bash
pip3 install pyyaml
```

### 编译 chrome-devtools-cli

chrome-auto-fetch 通过命令行调用 `chrome-devtools` (Windows 上是 `chrome-devtools.exe`) 来实现 CDP 操作。你需要先编译这个工具。

#### macOS

```bash
# 克隆项目
git clone https://github.com/aeroxy/chrome-devtools-cli.git
cd chrome-devtools-cli

# 编译 (release 模式, 编译时间约 2-5 分钟)
cargo build --release

# 复制二进制到 PATH 目录
cp target/release/chrome-devtools /usr/local/bin/

# 验证
chrome-devtools --help
```

**Homebrew 备选方案 (macOS):**

如果你用 Homebrew，也可以直接安装预编译版本，免去 Rust 编译:

```bash
brew install aeroxy/tap/chrome-devtools
chrome-devtools --help
```

#### Linux

```bash
# 安装编译工具 — 根据你的发行版选择:

# Debian/Ubuntu
sudo apt install build-essential pkg-config libssl-dev

# CentOS/RHEL 7
sudo yum install gcc gcc-c++ make pkg-config openssl-devel

# CentOS/RHEL 8 / Fedora
sudo dnf install gcc gcc-c++ make pkg-config openssl-devel

# Arch Linux
sudo pacman -S base-devel pkg-config openssl

# Alpine
apk add build-base pkg-config openssl-dev

# 克隆项目
git clone https://github.com/aeroxy/chrome-devtools-cli.git
cd chrome-devtools-cli

# 编译
cargo build --release

# 复制二进制到 PATH 目录 (需要 sudo)
sudo cp target/release/chrome-devtools /usr/local/bin/

# 验证
chrome-devtools --help
```

**Linux 依赖说明:**

- `build-essential` / `gcc gcc-c++ make` / `base-devel`: 编译工具链 (gcc、g++、make)
- `pkg-config`: 用于查找系统库
- `libssl-dev` / `openssl-devel` / `openssl`: OpenSSL 开发库，Rust 的 TLS 依赖需要

不同发行版包名对照:

| 发行版 | 编译工具包 | OpenSSL 开发包 |
|---|---|---|
| Debian/Ubuntu | `build-essential` | `libssl-dev` |
| CentOS/RHEL 7 | `gcc gcc-c++ make` | `openssl-devel` |
| CentOS/RHEL 8 / Fedora | `gcc gcc-c++ make` | `openssl-devel` |
| Arch Linux | `base-devel` | `openssl` |
| Alpine | `build-base` | `openssl-dev` |

**离线编译 (没有包管理器的 Linux):**

1. 在有网络的机器上编译好 `chrome-devtools` 二进制
2. 传到目标机器: `scp target/release/chrome-devtools user@remote:/usr/local/bin/`
3. 目标机器上无需安装 Rust 和编译工具

或者用静态链接方式编译 (无需目标机器有 OpenSSL):

```bash
# 在编译机器上设置静态链接
export OPENSSL_STATIC=1
cargo build --release --target x86_64-unknown-linux-musl
# 生成的二进制无动态依赖, 可直接复制到任何 Linux 运行
```

#### Windows

```powershell
# 前提: 已安装 Rust + Visual Studio Build Tools (含 C++ 工作负载)
# 在 "Developer Command Prompt" 或 "Developer PowerShell" 中执行

# 克隆项目
git clone https://github.com/aeroxy/chrome-devtools-cli.git
cd chrome-devtools-cli

# 编译
cargo build --release

# 复制二进制 (或者将 target\release 目录加入 PATH)
copy target\release\chrome-devtools.exe C:\tools\

# 将 C:\tools 添加到系统 PATH:
# 系统属性 → 高级 → 环境变量 → 在 PATH 中添加 C:\tools
```

**Windows 依赖安装 (winget 方式):**

```powershell
# 安装 Rust (包含 cargo)
winget install Rustlang.Rustup

# 安装 Visual Studio Build Tools (含 C++ 工作负载)
winget install Microsoft.VisualStudio.2022.BuildTools --override "--add Microsoft.VisualStudio.Workload.VCTools --includeRecommended --passive"
```

**Windows 依赖安装 (手动下载方式):**

没有 winget (旧版 Windows 或企业管控环境):

1. **Rust:** 从 [rustup.rs](https://rustup.rs/) 下载 `rustup-init.exe`，双击运行
2. **Visual Studio Build Tools:**
   - 从 [visualstudio.microsoft.com](https://visualstudio.microsoft.com/downloads/#build-tools-for-visual-studio-2022) 下载离线安装包
   - 运行安装，勾选 "Desktop development with C++"
   - 确保 "Windows 10/11 SDK" 和 "MSVC v143 build tools" 被选中
3. **离线方案:** 在另一台有网络的 Windows 机器上编译好 `chrome-devtools.exe`，用 U 盘/网络共享传到目标机器即可，目标机器无需安装 Rust 和 VS Build Tools

**Windows 编译失败怎么办?** 见 FAQ 第 5 条。

### 配置 Chrome 远程调试

这是整个工具能够运行的关键一步。理解它背后的原因很重要。

#### 为什么需要 --remote-debugging-port?

Chrome DevTools Protocol (CDP) 是 Chrome 提供的一套调试接口。默认情况下，Chrome 不允许外部程序通过 CDP 控制它。要启用 CDP，你需要:

- **方法 1:** 打开 `chrome://inspect` 页面，勾选 "Discover network targets"，添加目标地址：但这只对已运行的 Chrome 有效，不适用于自动化场景。
- **方法 2:** 启动 Chrome 时加上 `--remote-debugging-port` 参数：这是推荐的自动化方案。

方法 2 是必需的，因为 CDP 的权限确认弹窗 ("Chrome 正被自动测试软件控制") 无法通过任何方式绕过或自动关闭。

#### 端口冲突问题

你日常使用的 Chrome 默认占用 CDP 端口 9222。如果日常 Chrome 也在运行 (即使你没特意开启远程调试)，端口 9222 可能已被占用。所以:

- **日常 Chrome:** 端口 9222 (你平时浏览用的)
- **Debug Chrome:** 端口 9333 (专门给自动化用的)

两者互不干扰。启动脚本统一使用端口 9333。

#### macOS

```bash
# 1. 创建独立 profile 目录
mkdir -p ~/chrome-debug-profile

# 2. 启动 Chrome (关键: 必须用 open -na 强制新实例)
open -na "Google Chrome" --args \
    --remote-debugging-port=9333 \
    --user-data-dir="$HOME/chrome-debug-profile" \
    --no-first-run \
    --disable-background-networking \
    --disable-default-apps \
    --disable-extensions

# 3. 验证连接
curl -s http://127.0.0.1:9333/json/version
```

**关于 `open -na`:** macOS 上如果你直接用 `"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"` 启动，它可能会复用到已有的 Chrome 进程。`open -na` 确保每次都启动一个新实例，这是 macOS 特有的要求。

你也可以直接用项目自带的脚本:

```bash
bash scripts/start-chrome-debug.sh
```

这个脚本包含幂等检查：如果端口 9333 上已有 Chrome 在运行，它会直接打印 WebSocket 信息并跳过启动。

#### Linux

```bash
# 1. 创建独立 profile 目录
mkdir -p ~/chrome-debug-profile

# 2. 启动 Chrome (后台运行)
google-chrome --remote-debugging-port=9333 \
    --user-data-dir="$HOME/chrome-debug-profile" \
    --no-first-run \
    --disable-gpu \
    --disable-background-networking \
    --disable-default-apps \
    --disable-extensions &
# 或: google-chrome-stable ... &
# 或: chromium-browser ... &

# 3. 验证连接
curl -s http://127.0.0.1:9333/json/version
```

**如果以 root 用户运行**, 需要额外添加 `--no-sandbox` 参数:

```bash
google-chrome --remote-debugging-port=9333 \
    --user-data-dir="$HOME/chrome-debug-profile" \
    --no-first-run --disable-gpu --no-sandbox &
```

你也可以用项目自带的脚本:

```bash
bash scripts/start-chrome-debug-linux.sh
```

该脚本会自动查找 Chrome 二进制 (依次尝试 `google-chrome-stable`、`google-chrome`、`chromium-browser`、`chromium`)。

#### Windows

```bat
:: 1. 创建独立 profile 目录
mkdir %USERPROFILE%\chrome-debug-profile

:: 2. 启动 Chrome
start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" ^
    --remote-debugging-port=9333 ^
    --user-data-dir="%USERPROFILE%\chrome-debug-profile" ^
    --no-first-run ^
    --disable-background-networking ^
    --disable-default-apps ^
    --disable-extensions
```

如果 Chrome 安装在 `Program Files (x86)` 或其他路径，请相应调整。

你也可以双击运行项目自带的脚本:

```
scripts\start-chrome-debug.bat
```

该脚本会先检查 `C:\Program Files\Google\Chrome\Application\chrome.exe`，再检查 `C:\Program Files (x86)\Google\Chrome\Application\chrome.exe`。

**Windows 验证:**

打开浏览器，访问 `http://127.0.0.1:9333/json/version`。如果你能看到 JSON 格式的浏览器信息，说明远程调试已经成功启动。

#### 首次登录 (非常重要!)

启动 Debug Chrome 后，你需要**手动**在 Debug Chrome 窗口中登录目标网站 (输入账号密码、处理验证码等)。登录状态会保存在独立的 profile 目录中 (`~/chrome-debug-profile`)，之后每次启动都会复用。以后再运行自动化脚本时，就不需要重复登录了。

---

[← 返回主文档](../README.md)