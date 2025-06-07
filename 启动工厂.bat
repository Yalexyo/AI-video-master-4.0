@echo off
chcp 65001 >nul
title 母婴视频智能工厂

cls
echo 🏭 正在启动母婴视频智能工厂...
echo ======================================

REM 获取脚本所在目录
set "SCRIPT_DIR=%~dp0"
echo 📁 项目目录: %SCRIPT_DIR%

REM 切换到项目目录
cd /d "%SCRIPT_DIR%" || (
    echo ❌ 无法进入项目目录: %SCRIPT_DIR%
    pause
    exit /b 1
)

echo ✅ 已切换到项目目录

REM 检查虚拟环境是否存在
if exist ".venv" (
    echo ✅ 发现虚拟环境，正在激活...
    call .venv\Scripts\activate.bat || (
        echo ⚠️  虚拟环境激活失败，使用系统Python
    )
) else (
    echo ⚠️  未找到虚拟环境 ^(.venv^)，使用系统Python
)

REM 检查Python环境
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 错误：未找到Python
    echo 请先安装Python: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo ✅ Python环境检查通过

REM 检查streamlit是否已安装
streamlit --version >nul 2>&1
if errorlevel 1 (
    echo 📦 Streamlit未安装，正在安装...
    pip install streamlit || (
        echo ❌ Streamlit安装失败
        pause
        exit /b 1
    )
)

echo ✅ Streamlit检查通过

REM 切换到streamlit_app目录
if not exist "streamlit_app" (
    echo ❌ 错误：未找到streamlit_app目录
    echo 请确保您在正确的项目目录中运行此脚本
    pause
    exit /b 1
)

cd streamlit_app || (
    echo ❌ 无法进入streamlit_app目录
    pause
    exit /b 1
)

REM 检查主页.py是否存在
if not exist "主页.py" (
    echo ❌ 错误：未找到主页.py文件
    echo 当前目录: %CD%
    dir
    pause
    exit /b 1
)

echo ✅ 找到主页.py文件

REM 查找可用端口
set PORT=8501
echo 🔍 正在查找可用端口...

REM 检查端口是否被占用（Windows版本简化）
netstat -an | find ":%PORT% " >nul
if not errorlevel 1 (
    set /a PORT+=1
    echo ⚠️  端口 8501 已被占用，使用端口 %PORT%
)

echo ✅ 找到可用端口: %PORT%
echo 🚀 正在启动应用...
echo 🌐 应用地址: http://localhost:%PORT%
echo ======================================
echo 💡 提示：关闭此窗口将停止应用
echo 💡 按 Ctrl+C 可以停止应用
echo 💡 启动可能需要几秒钟，请稍候...
echo ======================================

REM 启动streamlit应用
echo 🎬 正在初始化Streamlit...
streamlit run 主页.py --server.port %PORT% --server.headless true --server.fileWatcherType none

echo.
echo 🏭 应用已停止
echo 感谢使用母婴视频智能工厂！
pause 