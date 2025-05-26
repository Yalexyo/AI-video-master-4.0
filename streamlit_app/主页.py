import streamlit as st

st.set_page_config(
    page_title="AI视频分析大师 3.0",
    page_icon="🎥",
    layout="wide"
)

st.title("🎥 AI视频分析大师 3.0")
st.markdown("---")

st.markdown("""
## 🌟 欢迎使用AI视频分析大师

### 📋 主要功能
- **🔍 视频分析** - 智能语音转录和语义分析
- **🎬 场景分段** - 专业级视频场景检测和切分
- **⚙️ 系统设置** - 配置API密钥和参数

### 🚀 快速开始
1. 点击左侧导航栏选择功能模块
2. 上传您的视频文件
3. 开始智能分析

### 📖 使用指南
- **视频分析**: 适用于内容理解和语义分段
- **场景分段**: 适用于视频剪辑和片段生成
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