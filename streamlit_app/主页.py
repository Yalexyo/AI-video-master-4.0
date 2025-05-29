import streamlit as st
import os
import json

st.set_page_config(
    page_title="AI视频分析大师 3.0",
    page_icon="🎥",
    layout="wide"
)

def check_google_cloud_credentials():
    """检查Google Cloud凭据状态"""
    creds_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
    
    if not creds_path:
        return False, "未设置环境变量"
    
    if not os.path.exists(creds_path):
        return False, "凭据文件不存在"
    
    try:
        with open(creds_path, 'r', encoding='utf-8') as f:
            creds_data = json.load(f)
        
        required_fields = ['type', 'project_id', 'private_key_id', 'private_key', 'client_email']
        missing_fields = [field for field in required_fields if field not in creds_data]
        
        if missing_fields:
            return False, f"缺少字段: {', '.join(missing_fields)}"
        
        return True, creds_data.get('project_id', 'N/A')
        
    except json.JSONDecodeError:
        return False, "JSON格式错误"
    except Exception as e:
        return False, f"读取失败: {str(e)}"

def check_dashscope_api_key():
    """检查DashScope API密钥状态"""
    api_key = os.environ.get('DASHSCOPE_API_KEY')
    return bool(api_key), len(api_key) if api_key else 0

st.title("🎥 AI视频分析大师 3.0")
st.markdown("---")

# 添加系统状态检查
st.markdown("### 📊 系统状态检查")

# Google Cloud凭据状态
gc_status, gc_info = check_google_cloud_credentials()
# DashScope API密钥状态  
ds_status, ds_key_length = check_dashscope_api_key()

col1, col2 = st.columns(2)

with col1:
    if gc_status:
        st.success(f"✅ **Google Cloud凭据**: 已配置 (项目: {gc_info})")
    else:
        st.error(f"❌ **Google Cloud凭据**: {gc_info}")
        st.warning("⚠️ Google Cloud Video Intelligence分析将无法使用")
        with st.expander("🔧 如何设置Google Cloud凭据"):
            st.markdown("""
            **方法1: 在设置页面上传**
            1. 点击左侧 ⚙️ 设置 页面
            2. 在"Google Cloud凭据"部分上传JSON文件
            
            **方法2: 环境变量设置**
            ```bash
            export GOOGLE_APPLICATION_CREDENTIALS=path/to/credentials.json
            ```
            
            **获取凭据文件:**
            1. 访问 [Google Cloud Console](https://console.cloud.google.com)
            2. 创建服务账户并下载JSON密钥文件
            3. 确保启用Video Intelligence API
            """)

with col2:
    if ds_status:
        st.success(f"✅ **DashScope API**: 已配置 (长度: {ds_key_length})")
    else:
        st.error("❌ **DashScope API**: 未设置")
        st.warning("⚠️ Qwen视觉分析将无法使用")
        with st.expander("🔧 如何设置DashScope API密钥"):
            st.markdown("""
            **在设置页面配置:**
            1. 点击左侧 ⚙️ 设置 页面
            2. 在"DashScope API"部分输入密钥
            
            **获取API密钥:**
            1. 访问 [阿里云DashScope](https://dashscope.console.aliyun.com/)
            2. 注册并创建API密钥
            3. 复制密钥到设置页面
            """)

st.markdown("---")

st.markdown("""
## 🌟 欢迎使用AI视频分析大师

### 📋 主要功能
- **🔍 视频分析** - 智能语音转录和语义分析
- **🔬 Google Cloud 视频智能测试** - 高精度视频内容分析
- **⚙️ 系统设置** - 配置API密钥和参数

### 🚀 快速开始
1. **首先确保上方系统状态显示正常** ⬆️
2. 点击左侧导航栏选择功能模块
3. 上传您的视频文件
4. 开始智能分析

### 📖 使用指南
- **视频分析**: 适用于内容理解和语义分段
- **Google Cloud测试**: 需要凭据配置，提供最高精度分析
- **系统设置**: 配置API密钥和高级参数

---
*选择左侧菜单开始使用*
""")

# 显示系统状态
col1, col2, col3 = st.columns(3)

with col1:
    st.metric("支持格式", "MP4, AVI, MOV", "多种视频格式")

with col2:
    st.metric("检测方法", "3种", "FFmpeg, Content, Histogram")

with col3:
    st.metric("语义类型", "10种", "广告开场, 产品介绍等") 