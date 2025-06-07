import streamlit as st
import os
import json

st.set_page_config(
    page_title="母婴视频智能工厂",
    page_icon="🏭",
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

def check_deepseek_api_key():
    """检查DeepSeek API密钥状态"""
    api_key = os.environ.get('DEEPSEEK_API_KEY')
    return bool(api_key), len(api_key) if api_key else 0

st.title("🏭 母婴视频智能工厂")
st.markdown("---")

# 工厂概述
st.markdown("""
### 🎯 **智能工厂概述**
**专为母婴奶粉营销视频打造的全自动化生产线**

通过AI驱动的三大工厂模块，实现从原料到成品的智能化视频生产：
""")

# 工厂流程图
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown("""
    ### 🧫 **零件工厂**
    **原料生产车间**
    
    **功能**: 标杆视频 → SRT字幕转换
    - 📤 上传标杆视频
    - 🎤 AI语音识别转录  
    - 📝 生成高精度SRT字幕
    - 💾 自动保存到指定目录
    
    **产出**: 标准化SRT字幕文件
    """)

with col2:
    st.markdown("""
    ### 🧱 **组装工厂** 
    **AI模型配置车间**
    
    **功能**: AI识别模型配置管理
    - 🤖 AI识别词库配置
    - 🔍 Prompt模板预览
    - 📊 配置验证与统计
    - ⚙️ 模型参数优化
    
    **产出**: 优化的AI分析配置
    """)

with col3:
    st.markdown("""
    ### 🐛 **调试工厂**
    **规则调试车间**
    
    **功能**: 业务分类规则配置与调试
    - 📋 映射规则详细检查
    - 🔬 片段分析调试  
    - 🧪 过滤机制测试
    - ✅ 实时效果验证
    
    **产出**: 精准的分类规则
    """)

with col4:
    st.markdown("""
    ### 🧪 **混剪工厂**
    **成品生产车间**
    
    **功能**: 智能视频合成与配置
    - 🎬 **混剪**: 视频片段映射与合成
    - 🤖 **参数设置**: AI模型配置管理
    - 📊 多种选择策略
    - 🎯 营销模块精准匹配
    
    **产出**: 高质量种草短片
    """)

st.markdown("---")

# 系统状态检查
st.markdown("### 📊 **工厂系统状态**")

# API状态检查
gc_status, gc_info = check_google_cloud_credentials()
ds_status, ds_key_length = check_dashscope_api_key()
deepseek_status, deepseek_key_length = check_deepseek_api_key()

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("#### 🔑 Google Cloud")
    if gc_status:
        st.success(f"✅ **已配置** (项目: {gc_info})")
    else:
        st.error(f"❌ **未配置**: {gc_info}")
        with st.expander("🔧 配置说明"):
            st.markdown("""
            **获取凭据:**
            1. 访问 [Google Cloud Console](https://console.cloud.google.com)
            2. 创建服务账户并下载JSON密钥
            3. 设置环境变量 `GOOGLE_APPLICATION_CREDENTIALS`
            """)

with col2:
    st.markdown("#### 🎯 Qwen模型 (DashScope)")
    if ds_status:
        st.success(f"✅ **已配置** (长度: {ds_key_length})")
    else:
        st.error("❌ **未配置**")
        with st.expander("🔧 配置说明"):
            st.markdown("""
            **获取API密钥:**
            1. 访问 [阿里云DashScope](https://dashscope.console.aliyun.com/)
            2. 注册并创建API密钥
            3. 设置环境变量 `DASHSCOPE_API_KEY`
            """)

with col3:
    st.markdown("#### 🧠 DeepSeek模型")
    if deepseek_status:
        st.success(f"✅ **已配置** (长度: {deepseek_key_length})")
    else:
        st.error("❌ **未配置**")
        with st.expander("🔧 配置说明"):
            st.markdown("""
            **获取API密钥:**
            1. 访问 [DeepSeek官网](https://www.deepseek.com/)
            2. 注册并获取API密钥
            3. 设置环境变量 `DEEPSEEK_API_KEY`
            """)

st.markdown("---")

# 工作流程指导
st.markdown("### 🚀 **智能生产流程**")

st.markdown("""
#### 📋 **推荐工作流程**

```
准备阶段: 🧱 组装工厂 → AI识别词库配置 + 🐛 调试工厂 → 业务分类规则配置
     ↓
步骤1: 🧫 零件工厂 → 处理标杆视频，生成SRT字幕文件
     ↓  
步骤2: 🧪 混剪工厂 → 视频分析 → 场景聚合 → 智能标签生成 → 营销视频合成
     │    🎬 视频分析与切分 → 🧠 场景聚合 → 🏷️ 智能标签工厂 → 🎯 精准合成
     ↓
调试优化: 🐛 调试工厂 → 实时调试分类规则，优化识别效果
```

#### ✨ **核心优势**
- 🤖 **全AI驱动**: Qwen + DeepSeek双模型智能分析
- 🎯 **营销专精**: 针对母婴奶粉领域优化
- ⚡ **高效批量**: 支持大规模视频自动化处理
- 📊 **质量保证**: 多层质量检测与智能兜底
- 🔧 **实时调试**: 配置+调试一体化，立即验证效果
- 🔄 **流程自动**: 从配置到成品全链路智能化
""")

# 状态统计
st.markdown("---")
col1, col2, col3, col4 = st.columns(4)

with col1:
    api_count = sum([gc_status, ds_status, deepseek_status])
    st.metric("API配置状态", f"{api_count}/3", "个已配置")

with col2:
    st.metric("工厂模块", "4个", "零件+组装+调试+混剪")

with col3:
    st.metric("AI模型", "2个", "Qwen + DeepSeek")

with col4:
    st.metric("营销模块", "4类", "痛点+方案+卖点+促销")

st.markdown("---")
st.markdown("""
### 🎊 **开始使用**
点击左侧导航栏，选择对应的工厂模块开始视频智能生产！

**💡 提示**: 建议按照 🧫→🧱→🧪 的顺序使用各个工厂模块，以获得最佳体验。
""") 