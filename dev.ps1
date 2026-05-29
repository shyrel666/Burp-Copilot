<#
.SYNOPSIS
    本地开发一键启动脚本：同时拉起后端 (FastAPI/uvicorn --reload) 和前端 (Vite dev)。

.DESCRIPTION
    - 首次运行会自动为后端创建 .venv 虚拟环境并安装依赖。
    - 之后直接复用环境，在两个独立窗口分别启动后端和前端，均带热重载。
    - 关闭对应窗口即可停止服务。

.PARAMETER Reinstall
    强制重新安装后端依赖（升级依赖后使用）。

.EXAMPLE
    .\dev.ps1
    .\dev.ps1 -Reinstall
#>
param(
    [switch]$Reinstall
)

$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$backend = Join-Path $root 'backend'
$frontend = Join-Path $root 'frontend'
$venv = Join-Path $backend '.venv'
$venvPython = Join-Path $venv 'Scripts\python.exe'

Write-Host '== Burp Copilot 本地开发启动 ==' -ForegroundColor Cyan

# 1) 后端虚拟环境 + 依赖（幂等）
if ($Reinstall -or -not (Test-Path $venvPython)) {
    if (-not (Test-Path $venvPython)) {
        Write-Host '[backend] 创建虚拟环境 .venv ...' -ForegroundColor Yellow
        python -m venv $venv
    }
    Write-Host '[backend] 安装依赖 (pip install -e ".[dev]") ...' -ForegroundColor Yellow
    & $venvPython -m pip install --upgrade pip
    & $venvPython -m pip install -e "$backend[dev]"
} else {
    Write-Host '[backend] 已存在虚拟环境，跳过安装。' -ForegroundColor DarkGray
}

# 2) 前端依赖（幂等）
if (-not (Test-Path (Join-Path $frontend 'node_modules'))) {
    Write-Host '[frontend] 安装依赖 (npm install) ...' -ForegroundColor Yellow
    Push-Location $frontend
    npm install
    Pop-Location
} else {
    Write-Host '[frontend] 已存在 node_modules，跳过安装。' -ForegroundColor DarkGray
}

# 3) 在独立窗口启动后端（uvicorn --reload）
$backendCmd = "& '$venv\Scripts\Activate.ps1'; uvicorn app.main:app --reload --port 8000"
Start-Process powershell -WorkingDirectory $backend -ArgumentList '-NoExit', '-Command', $backendCmd

# 4) 在独立窗口启动前端（vite dev，默认 http://127.0.0.1:5173）
Start-Process powershell -WorkingDirectory $frontend -ArgumentList '-NoExit', '-Command', 'npm run dev'

Write-Host ''
Write-Host '后端:  http://127.0.0.1:8000   (API 文档: /docs)' -ForegroundColor Green
Write-Host '前端:  http://127.0.0.1:5173' -ForegroundColor Green
Write-Host ''
Write-Host '提示: 前端默认连后端 127.0.0.1:8000，开发模式无需 BACKEND_TOKEN。' -ForegroundColor DarkGray
Write-Host '      若要使用 LLM 分析，请在后端配置 OPENAI_API_KEY（环境变量或 .env）。' -ForegroundColor DarkGray
Write-Host '      停止服务：关闭弹出的两个 PowerShell 窗口即可。' -ForegroundColor DarkGray
