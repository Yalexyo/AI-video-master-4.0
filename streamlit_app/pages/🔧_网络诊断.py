"""
网络诊断页面

帮助用户诊断和解决DashScope连接问题
"""

import streamlit as st
import os
import requests
from pathlib import Path

# 尝试导入网络配置模块
try:
    from streamlit_app.config.network_config import diagnose_connection_issues, get_network_config
    NETWORK_CONFIG_AVAILABLE = True
except ImportError:
    NETWORK_CONFIG_AVAILABLE = False

st.set_page_config(
    page_title="网络诊断 - AI视频分析大师",
    page_icon="🔧",
    layout="wide"
)

st.title("🔧 网络诊断")
st.markdown("---")

st.markdown("""
### 📡 DashScope连接诊断

此页面帮助您诊断和解决DashScope API连接问题。从终端显示的错误信息来看，主要问题是：

1. **代理连接错误**: `ProxyError('Unable to connect to proxy')`
2. **数据类型错误**: `'list' object has no attribute 'split'`

让我们一步步解决这些问题。
""")

# 显示当前环境变量状态
st.subheader("🔍 当前环境配置")

with st.expander("查看环境变量", expanded=True):
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**API配置:**")
        dashscope_key = os.environ.get("DASHSCOPE_API_KEY")
        if dashscope_key:
            masked_key = f"{dashscope_key[:8]}...{dashscope_key[-4:]}" if len(dashscope_key) > 12 else "*" * len(dashscope_key[8:])
            st.success(f"✅ DASHSCOPE_API_KEY: {masked_key}")
        else:
            st.error("❌ DASHSCOPE_API_KEY: 未设置")
        
        st.write(f"**Base URL:** {os.environ.get('DASHSCOPE_BASE_URL', 'https://dashscope.aliyuncs.com')}")
        st.write(f"**连接超时:** {os.environ.get('CONNECTION_TIMEOUT', '30')}秒")
        st.write(f"**最大重试次数:** {os.environ.get('MAX_RETRIES', '3')}")
    
    with col2:
        st.write("**代理配置:**")
        use_proxy = os.environ.get("USE_PROXY", "false").lower() == "true"
        st.write(f"**使用代理:** {'是' if use_proxy else '否'}")
        
        if use_proxy:
            http_proxy = os.environ.get("HTTP_PROXY")
            https_proxy = os.environ.get("HTTPS_PROXY")
            no_proxy = os.environ.get("NO_PROXY")
            
            if http_proxy:
                st.write(f"**HTTP代理:** {http_proxy}")
            if https_proxy:
                st.write(f"**HTTPS代理:** {https_proxy}")
            if no_proxy:
                st.write(f"**代理例外:** {no_proxy}")
        else:
            st.info("当前未配置代理")

st.markdown("---")

# 快速修复建议
st.subheader("🚀 快速修复建议")

st.markdown("""
基于您当前遇到的错误，以下是推荐的解决方案：

### 1. 🚫 禁用代理（推荐）
如果您不需要代理或代理配置有问题，可以直接禁用：
""")

# 代理禁用按钮
col1, col2 = st.columns([1, 2])
with col1:
    if st.button("禁用代理", type="primary"):
        os.environ["USE_PROXY"] = "false"
        # 清除代理设置
        for key in ["HTTP_PROXY", "HTTPS_PROXY", "NO_PROXY"]:
            os.environ.pop(key, None)
        st.success("✅ 代理已禁用！请重新启动应用程序。")
        st.info("请在终端中停止应用程序（Ctrl+C）然后重新运行：`streamlit run streamlit_app/主页.py`")

with col2:
    st.code("""
# 或者在终端中运行：
export USE_PROXY=false
unset HTTP_PROXY
unset HTTPS_PROXY
unset NO_PROXY
""")

st.markdown("### 2. 🔑 检查API密钥")
if not os.environ.get("DASHSCOPE_API_KEY"):
    st.error("您需要设置DashScope API密钥")
    api_key_input = st.text_input("请输入您的DashScope API密钥:", type="password")
    if st.button("设置API密钥") and api_key_input:
        os.environ["DASHSCOPE_API_KEY"] = api_key_input
        st.success("✅ API密钥已设置！")

st.markdown("---")

# 连接测试
st.subheader("🌐 连接测试")

if st.button("测试网络连接", type="primary"):
    with st.spinner("正在测试连接..."):
        # 简单的连接测试
        test_results = {}
        
        # 测试基本互联网连接
        try:
            response = requests.get("https://www.baidu.com", timeout=10)
            if response.status_code == 200:
                test_results["internet"] = "✅ 基本互联网连接正常"
            else:
                test_results["internet"] = f"⚠️ 互联网连接异常，状态码: {response.status_code}"
        except Exception as e:
            test_results["internet"] = f"❌ 互联网连接失败: {str(e)}"
        
        # 测试DashScope连接
        try:
            dashscope_url = "https://dashscope.aliyuncs.com"
            proxies = None
            
            if os.environ.get("USE_PROXY", "false").lower() == "true":
                proxies = {}
                if os.environ.get("HTTP_PROXY"):
                    proxies["http"] = os.environ.get("HTTP_PROXY")
                if os.environ.get("HTTPS_PROXY"):
                    proxies["https"] = os.environ.get("HTTPS_PROXY")
            
            response = requests.get(dashscope_url, timeout=30, proxies=proxies)
            if response.status_code in [200, 403, 404]:
                test_results["dashscope"] = "✅ DashScope服务可访问"
            else:
                test_results["dashscope"] = f"⚠️ DashScope连接异常，状态码: {response.status_code}"
        except requests.exceptions.ProxyError as e:
            test_results["dashscope"] = f"❌ 代理连接失败: {str(e)}"
        except requests.exceptions.ConnectTimeout as e:
            test_results["dashscope"] = f"❌ 连接超时: {str(e)}"
        except requests.exceptions.ConnectionError as e:
            test_results["dashscope"] = f"❌ 连接错误: {str(e)}"
        except Exception as e:
            test_results["dashscope"] = f"❌ 未知网络错误: {str(e)}"
        
        # 显示测试结果
        st.subheader("📊 测试结果")
        for test_name, result in test_results.items():
            if "✅" in result:
                st.success(result)
            elif "⚠️" in result:
                st.warning(result)
            else:
                st.error(result)

st.markdown("---")

# 环境变量配置器
st.subheader("⚙️ 环境变量配置")

with st.expander("配置环境变量", expanded=False):
    st.markdown("### API配置")
    
    # API密钥输入
    current_key = os.environ.get("DASHSCOPE_API_KEY", "")
    new_api_key = st.text_input(
        "DashScope API密钥",
        value=current_key,
        type="password",
        help="输入您的DashScope API密钥"
    )
    
    st.markdown("### 代理配置")
    
    col1, col2 = st.columns(2)
    
    with col1:
        use_proxy = st.checkbox(
            "使用代理",
            value=os.environ.get("USE_PROXY", "false").lower() == "true"
        )
        
        http_proxy = st.text_input(
            "HTTP代理",
            value=os.environ.get("HTTP_PROXY", ""),
            disabled=not use_proxy,
            help="格式: http://proxy_server:port"
        )
    
    with col2:
        https_proxy = st.text_input(
            "HTTPS代理",
            value=os.environ.get("HTTPS_PROXY", ""),
            disabled=not use_proxy,
            help="格式: http://proxy_server:port"
        )
        
        no_proxy = st.text_input(
            "代理例外",
            value=os.environ.get("NO_PROXY", ""),
            disabled=not use_proxy,
            help="格式: localhost,127.0.0.1,*.local"
        )
    
    if st.button("应用配置"):
        # 设置环境变量
        if new_api_key:
            os.environ["DASHSCOPE_API_KEY"] = new_api_key
            st.success("✅ API密钥已更新")
        
        os.environ["USE_PROXY"] = str(use_proxy).lower()
        
        if use_proxy:
            if http_proxy:
                os.environ["HTTP_PROXY"] = http_proxy
            if https_proxy:
                os.environ["HTTPS_PROXY"] = https_proxy
            if no_proxy:
                os.environ["NO_PROXY"] = no_proxy
        else:
            # 清除代理设置
            for key in ["HTTP_PROXY", "HTTPS_PROXY", "NO_PROXY"]:
                os.environ.pop(key, None)
        
        st.success("✅ 配置已应用！建议重新启动应用程序以确保配置生效。")

st.markdown("---")

# 故障排除指南
st.subheader("📖 故障排除指南")

with st.expander("常见问题解决方案", expanded=False):
    st.markdown("""
    ### 🔸 连接错误 (ProxyError)
    - **原因**: 代理配置不正确或代理服务器不可用
    - **解决方案**: 
      1. 点击上方"禁用代理"按钮
      2. 检查代理服务器地址和端口是否正确
      3. 确认代理服务器是否正常运行
    
    ### 🔸 连接超时 (Timeout)
    - **原因**: 网络连接缓慢或防火墙阻止连接
    - **解决方案**:
      1. 增加连接超时时间
      2. 检查防火墙设置
      3. 确认网络连接稳定
    
    ### 🔸 API密钥错误
    - **原因**: API密钥未设置或不正确
    - **解决方案**:
      1. 在阿里云控制台获取正确的API密钥
      2. 确保密钥有足够的权限
      3. 重新设置DASHSCOPE_API_KEY环境变量
    
    ### 🔸 数据类型错误 ('list' object has no attribute 'split')
    - **原因**: API返回的数据格式不符合预期
    - **解决方案**: 这个问题已在最新版本中修复，重新启动应用即可
    """)

# 重启应用建议
st.info("""
💡 **重要提示**: 修改环境变量后，建议重新启动Streamlit应用程序以确保配置生效。

在终端中按 `Ctrl+C` 停止应用，然后重新运行：
```bash
streamlit run streamlit_app/主页.py
```
""")

# 技术支持信息
st.markdown("---")
st.info("""
💬 **需要更多帮助？**
- 查看 [DashScope官方文档](https://help.aliyun.com/zh/dashscope/)
- 检查网络设置和防火墙配置
- 联系您的网络管理员（如在企业环境中）
""") 