"""
⚙️ 系统设置页面

用户可以在此页面自定义：
- 目标人群列表
- 核心卖点列表  
- 产品类型列表
- LLM分析Prompt模板
"""

import streamlit as st
import json
import os
from pathlib import Path
import sys
import time

# 设置页面配置和样式
st.markdown("""
<style>
    /* 侧边栏宽度控制 - 与主页面保持一致 */
    .css-1d391kg {
        width: 180px !important;
        min-width: 180px !important;
        max-width: 180px !important;
    }
    
    .css-1lcbmhc {
        width: 180px !important;
        min-width: 180px !important;
        max-width: 180px !important;
    }
    
    .css-18e3th9 {
        padding-left: 200px !important;
    }
    
    section[data-testid="stSidebar"] {
        width: 180px !important;
        min-width: 180px !important;
        max-width: 180px !important;
    }
    
    section[data-testid="stSidebar"] > div {
        width: 180px !important;
        min-width: 180px !important;
        max-width: 180px !important;
    }
    
    .css-1v0mbdj a {
        font-size: 0.9rem !important;
        padding: 0.5rem 0.75rem !important;
    }
    
    .css-1cypcdb {
        display: none !important;
    }
    
    /* 设置页面特定样式 */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
</style>
""", unsafe_allow_html=True)

# 添加项目根目录到路径
ROOT_DIR = Path(__file__).parent.parent.parent
sys.path.append(str(ROOT_DIR))

from streamlit_app.config.config import get_config, save_config, get_semantic_segment_types, get_semantic_modules, TARGET_GROUPS
from streamlit_app.modules.analysis.segment_analyzer import DEFAULT_ANALYSIS_PROMPT
from streamlit_app.modules.data_process.semantic_type_editor import render_semantic_type_editor, render_semantic_type_quick_actions

def load_current_settings():
    """加载当前配置设置"""
    config = get_config()
    return {
        "target_groups": config.get("TARGET_GROUPS", ["孕期妈妈", "二胎妈妈", "混养妈妈", "新手爸妈", "贵妇妈妈"]),
        "selling_points": config.get("SELLING_POINTS", ["HMO & 母乳低聚糖", "自愈力", "品牌实力", "A2奶源", "开盖即饮", "精准配比"]),
        "product_types": config.get("PRODUCT_TYPES", ["启赋水奶", "启赋蕴淳", "启赋蓝钻"]),
        "analysis_prompt": config.get("ANALYSIS_PROMPT", DEFAULT_ANALYSIS_PROMPT)
    }

def save_settings(settings):
    """保存设置到配置文件"""
    try:
        config = get_config()
        config.update({
            "TARGET_GROUPS": settings["target_groups"],
            "SELLING_POINTS": settings["selling_points"], 
            "PRODUCT_TYPES": settings["product_types"],
            "ANALYSIS_PROMPT": settings["analysis_prompt"]
        })
        
        # 如果有语义类型的编辑，也保存到配置中
        if 'editing_semantic_types' in st.session_state and st.session_state.editing_semantic_types:
            # 确保"其他"类型始终存在且在最后
            semantic_types = st.session_state.editing_semantic_types.copy()
            if "其他" not in semantic_types:
                semantic_types.append("其他")
            elif semantic_types[-1] != "其他":
                # 将"其他"移到最后
                semantic_types.remove("其他")
                semantic_types.append("其他")
            config["SEMANTIC_SEGMENT_TYPES"] = semantic_types
        
        save_config(config)
        return True
    except Exception as e:
        st.error(f"保存设置失败: {str(e)}")
        return False

def main():
    """设置页面主函数"""
    st.title("⚙️ 设置")
    st.markdown("在这里可以自定义配置项，让分析更符合您的需求。")
    
    # 创建标签页
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🎯 目标人群", 
        "💎 核心卖点", 
        "📦 产品类型",
        "🎬 语义类型", 
        "🤖 AI分析设置"
    ])
    
    # 加载当前设置
    if 'settings' not in st.session_state:
        st.session_state.settings = load_current_settings()
    
    # 目标人群设置
    with tab1:
        st.subheader("🎯 目标人群配置")
        st.markdown("定义视频分析中可能涉及的目标人群类型")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # 当前目标人群列表
            st.markdown("**当前目标人群：**")
            for i, group in enumerate(st.session_state.settings["target_groups"]):
                cols = st.columns([4, 1])
                with cols[0]:
                    new_value = st.text_input(f"人群 {i+1}", value=group, key=f"target_group_{i}")
                    st.session_state.settings["target_groups"][i] = new_value
                with cols[1]:
                    if st.button("🗑️", key=f"del_target_{i}", help="删除此人群"):
                        st.session_state.settings["target_groups"].pop(i)
                        st.experimental_rerun()
            
            # 添加新人群
            st.markdown("**添加新人群：**")
            new_group = st.text_input("新人群名称", key="new_target_group")
            if st.button("➕ 添加人群") and new_group.strip():
                st.session_state.settings["target_groups"].append(new_group.strip())
                st.experimental_rerun()
        
        with col2:
            st.markdown("**预览效果：**")
            st.info("筛选器中将显示以下选项：")
            for group in st.session_state.settings["target_groups"]:
                st.markdown(f"• {group}")
    
    # 核心卖点设置
    with tab2:
        st.subheader("💎 核心卖点配置")
        st.markdown("定义产品可能具备的核心卖点")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # 当前卖点列表
            st.markdown("**当前核心卖点：**")
            for i, point in enumerate(st.session_state.settings["selling_points"]):
                cols = st.columns([4, 1])
                with cols[0]:
                    new_value = st.text_input(f"卖点 {i+1}", value=point, key=f"selling_point_{i}")
                    st.session_state.settings["selling_points"][i] = new_value
                with cols[1]:
                    if st.button("🗑️", key=f"del_selling_{i}", help="删除此卖点"):
                        st.session_state.settings["selling_points"].pop(i)
                        st.experimental_rerun()
            
            # 添加新卖点
            st.markdown("**添加新卖点：**")
            new_point = st.text_input("新卖点名称", key="new_selling_point")
            if st.button("➕ 添加卖点") and new_point.strip():
                st.session_state.settings["selling_points"].append(new_point.strip())
                st.experimental_rerun()
        
        with col2:
            st.markdown("**预览效果：**")
            st.info("AI将从以下卖点中识别：")
            for point in st.session_state.settings["selling_points"]:
                st.markdown(f"• {point}")
    
    # 产品类型设置
    with tab3:
        st.subheader("📦 产品类型配置")
        st.markdown("定义可能出现在视频中的产品类型")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # 当前产品类型列表
            st.markdown("**当前产品类型：**")
            for i, product in enumerate(st.session_state.settings["product_types"]):
                cols = st.columns([4, 1])
                with cols[0]:
                    new_value = st.text_input(f"产品 {i+1}", value=product, key=f"product_type_{i}")
                    st.session_state.settings["product_types"][i] = new_value
                with cols[1]:
                    if st.button("🗑️", key=f"del_product_{i}", help="删除此产品"):
                        st.session_state.settings["product_types"].pop(i)
                        st.experimental_rerun()
            
            # 添加新产品类型
            st.markdown("**添加新产品类型：**")
            new_product = st.text_input("新产品类型名称", key="new_product_type")
            if st.button("➕ 添加产品类型") and new_product.strip():
                st.session_state.settings["product_types"].append(new_product.strip())
                st.experimental_rerun()
        
        with col2:
            st.markdown("**预览效果：**")
            st.info("AI将从以下产品中识别：")
            for product in st.session_state.settings["product_types"]:
                st.markdown(f"• {product}")
    
    # 标签页4：语义类型设置
    with tab4:
        st.header("🎬 语义类型设置")
        st.markdown("配置视频片段的语义分类类型，用于自动分析和组织视频内容。")
        
        # 使用新的语义类型编辑器
        render_semantic_type_editor()
        
        st.markdown("---")
        
        # 快速操作
        render_semantic_type_quick_actions()
    
    # 标签页5：AI分析设置
    with tab5:
        st.subheader("🤖 AI分析设置")
        st.markdown("自定义发送给大模型的分析指令")
        
        col1, col2 = st.columns([3, 2])
        
        with col1:
            st.markdown("**分析Prompt模板：**")
            st.info("💡 在prompt中使用 {product_types} 和 {selling_points} 占位符，系统会自动替换为上面配置的列表")
            
            prompt_text = st.text_area(
                "编辑分析指令",
                value=st.session_state.settings["analysis_prompt"],
                height=400,
                help="这是发送给AI模型的完整指令，请谨慎修改"
            )
            st.session_state.settings["analysis_prompt"] = prompt_text
            
            # 重置按钮
            if st.button("🔄 重置为默认Prompt"):
                st.session_state.settings["analysis_prompt"] = DEFAULT_ANALYSIS_PROMPT
                st.experimental_rerun()
        
        with col2:
            st.markdown("**Prompt预览：**")
            # 显示替换后的prompt预览
            preview_prompt = prompt_text.format(
                product_types=str(st.session_state.settings["product_types"]),
                selling_points=str(st.session_state.settings["selling_points"])
            )
            st.code(preview_prompt, language="text")
    
    # 保存设置按钮
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col2:
        if st.button("💾 保存所有设置", type="primary", use_container_width=True):
            if save_settings(st.session_state.settings):
                st.success("✅ 设置已成功保存！")
                st.balloons()
                # 清除缓存以确保新设置生效
                if hasattr(st, 'cache_data'):
                    st.cache_data.clear()
            else:
                st.error("❌ 设置保存失败，请检查权限")
    
    # 底部说明
    st.markdown("---")
    st.markdown("""
    ### 📖 使用说明
    
    1. **目标人群**：定义视频分析中的受众分类，影响筛选器选项
    2. **核心卖点**：AI将从这些选项中识别视频片段的卖点
    3. **产品类型**：AI将从这些选项中识别视频中提到的产品
    4. **AI分析设置**：自定义发送给大模型的完整分析指令
    
    💡 **提示**：修改设置后需要重新分析视频才能看到效果。建议在分析前先完成所有配置。
    """)

if __name__ == "__main__":
    main() 