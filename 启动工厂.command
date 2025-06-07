#!/bin/bash

# 母婴视频智能工厂启动脚本
# 双击此文件即可启动应用

# 处理zsh安全问题
export ZSH_DISABLE_COMPFIX=true

clear
echo "🏭 正在启动母婴视频智能工厂..."
echo "======================================"

# 获取脚本所在目录的绝对路径
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
echo "📁 项目目录: $SCRIPT_DIR"

# 切换到项目目录
cd "$SCRIPT_DIR" || {
    echo "❌ 无法进入项目目录: $SCRIPT_DIR"
    read -p "按任意键退出..."
    exit 1
}

echo "✅ 已切换到项目目录"

# 检查并激活虚拟环境
if [ -d ".venv" ]; then
    echo "✅ 发现虚拟环境，正在激活..."
    source .venv/bin/activate || {
        echo "⚠️  虚拟环境激活失败，使用系统Python"
    }
else
    echo "⚠️  未找到虚拟环境 (.venv)，使用系统Python"
fi

# 检查Python环境
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误：未找到Python3"
    echo "请先安装Python3: https://www.python.org/downloads/"
    read -p "按任意键退出..."
    exit 1
fi

echo "✅ Python环境检查通过"

# 检查streamlit是否已安装
if ! command -v streamlit &> /dev/null; then
    echo "📦 Streamlit未安装，正在安装..."
    pip3 install streamlit || {
        echo "❌ Streamlit安装失败"
        read -p "按任意键退出..."
        exit 1
    }
fi

echo "✅ Streamlit检查通过"

# 切换到streamlit_app目录
if [ ! -d "streamlit_app" ]; then
    echo "❌ 错误：未找到streamlit_app目录"
    echo "请确保您在正确的项目目录中运行此脚本"
    read -p "按任意键退出..."
    exit 1
fi

cd streamlit_app || {
    echo "❌ 无法进入streamlit_app目录"
    read -p "按任意键退出..."
    exit 1
}

# 检查主页.py是否存在
if [ ! -f "主页.py" ]; then
    echo "❌ 错误：未找到主页.py文件"
    echo "当前目录: $(pwd)"
    echo "目录内容: $(ls -la)"
    read -p "按任意键退出..."
    exit 1
fi

echo "✅ 找到主页.py文件"

# 查找可用端口
PORT=8501
echo "🔍 正在查找可用端口..."
while lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1; do
    echo "⚠️  端口 $PORT 已被占用，尝试端口 $((PORT+1))"
    PORT=$((PORT+1))
    # 防止无限循环
    if [ $PORT -gt 8510 ]; then
        echo "❌ 无法找到可用端口 (8501-8510)"
        read -p "按任意键退出..."
        exit 1
    fi
done

echo "✅ 找到可用端口: $PORT"
echo "🚀 正在启动应用..."
echo "🌐 应用地址: http://localhost:$PORT"
echo "======================================"
echo "💡 提示：关闭此窗口将停止应用"
echo "💡 按 Ctrl+C 可以停止应用"
echo "💡 启动可能需要几秒钟，请稍候..."
echo "======================================"

# 启动streamlit应用
echo "🎬 正在初始化Streamlit..."
streamlit run 主页.py --server.port $PORT --server.headless true --server.fileWatcherType none

echo ""
echo "🏭 应用已停止"
echo "感谢使用母婴视频智能工厂！"
read -p "按任意键关闭窗口..." 