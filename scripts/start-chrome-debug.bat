@echo off
REM Windows Chrome 远程调试启动脚本
REM 使用独立 profile 启动 Chrome, 与日常 Chrome 并存
REM 日常 Chrome 占用端口 9222, debug Chrome 使用端口 9333

set PROFILE_DIR=%USERPROFILE%\chrome-debug-profile
set PORT=9333

REM 幂等检查: 如果 debug Chrome 已在运行, 跳过启动
curl -s http://127.0.0.1:%PORT%/json/version > nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo Debug Chrome 已在运行 (端口 %PORT%)
    echo WebSocket 信息:
    curl -s http://127.0.0.1:%PORT%/json/version
    goto :eof
)

REM 创建 profile 目录 (如果不存在)
if not exist "%PROFILE_DIR%" mkdir "%PROFILE_DIR%"

REM 查找 Chrome 二进制
set CHROME_PATH=
if exist "C:\Program Files\Google\Chrome\Application\chrome.exe" (
    set CHROME_PATH=C:\Program Files\Google\Chrome\Application\chrome.exe
) else if exist "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe" (
    set CHROME_PATH=C:\Program Files (x86)\Google\Chrome\Application\chrome.exe
) else (
    echo 错误: 未找到 Chrome
    echo 请安装 Chrome: https://www.google.com/chrome/
    exit /b 1
)

echo 使用 Chrome: %CHROME_PATH%

REM 启动 Chrome
start "" "%CHROME_PATH%" ^
    --remote-debugging-port=%PORT% ^
    --user-data-dir="%PROFILE_DIR%" ^
    --no-first-run ^
    --disable-background-networking ^
    --disable-default-apps ^
    --disable-extensions

REM 等待 Chrome 启动并验证连接
echo 等待 Chrome 启动...
set COUNT=0
:wait_loop
set /a COUNT+=1
if %COUNT% GTR 10 (
    echo 警告: Chrome 启动超时, 请检查 Chrome 是否正常运行
    exit /b 1
)
timeout /t 1 /nobreak > nul
curl -s http://127.0.0.1:%PORT%/json/version > nul 2>&1
if %ERRORLEVEL% NEQ 0 goto wait_loop

echo Chrome 已启动, 远程调试端口: %PORT%
echo WebSocket 信息:
curl -s http://127.0.0.1:%PORT%/json/version