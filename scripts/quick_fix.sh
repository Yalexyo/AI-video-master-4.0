#!/bin/bash

# DashScope快速修复脚本
# 解决常见的连接和配置问题

echo "🔧 DashScope 快速修复工具"
echo "=============================="

# 1. 禁用代理设置
echo ""
echo "1. 禁用代理设置..."
export USE_PROXY=false
unset HTTP_PROXY
unset HTTPS_PROXY  
unset NO_PROXY

echo "✅ 代理已禁用"

# 2. 检查API密钥
echo ""
echo "2. 检查API密钥..."
if [ -z "$DASHSCOPE_API_KEY" ]; then
    echo "❌ DASHSCOPE_API_KEY 未设置"
    echo "请运行: export DASHSCOPE_API_KEY='your_api_key_here'"
else
    echo "✅ DASHSCOPE_API_KEY 已设置"
fi

# 3. 设置网络配置
echo ""
echo "3. 优化网络配置..."
export CONNECTION_TIMEOUT=60
export MAX_RETRIES=3
echo "✅ 网络配置已优化"

# 4. 显示修复结果
echo ""
echo "📊 修复结果:"
echo "- 代理: 已禁用"
echo "- 连接超时: ${CONNECTION_TIMEOUT}秒"
echo "- 最大重试: ${MAX_RETRIES}次"

echo ""
echo "💡 接下来请："
echo "1. 重新启动Streamlit应用 (Ctrl+C 后重新运行)"
echo "2. 如果问题仍然存在，请检查网络连接"
echo "3. 确认API密钥是否正确设置"

echo ""
echo "🚀 修复完成！" 