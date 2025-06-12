"""
语义类型定义编辑器模块
用于配置和管理各个语义类型的详细定义
"""

import streamlit as st
import json
import copy
from typing import Dict, List, Any

from config.config import (
    get_semantic_type_definitions, 
    DEFAULT_SEMANTIC_TYPE_DEFINITIONS,
    DEFAULT_SEMANTIC_SEGMENT_TYPES,
    USER_CONFIG_FILE
)

@st.cache_data(ttl=60)
def load_semantic_definitions() -> Dict[str, Any]:
    """加载语义类型定义（带缓存）"""
    return get_semantic_type_definitions()

def save_semantic_definitions(definitions: Dict[str, Any]) -> bool:
    """保存语义类型定义到用户配置文件
    
    Args:
        definitions: 语义类型定义字典
        
    Returns:
        bool: 保存是否成功
    """
    try:
        # 读取现有配置
        try:
            with open(USER_CONFIG_FILE, "r", encoding="utf-8") as f:
                user_config = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            user_config = {}
        
        # 更新语义类型定义
        user_config["SEMANTIC_TYPE_DEFINITIONS"] = definitions
        
        # 保存配置
        with open(USER_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(user_config, f, ensure_ascii=False, indent=2)
        
        # 清除缓存以便重新加载
        load_semantic_definitions.clear()
        
        return True
    except Exception as e:
        st.error(f"保存配置失败: {e}")
        return False

def render_semantic_type_editor():
    """渲染语义类型编辑器界面"""
    
    st.markdown("### 📝 语义类型设置")
    st.markdown("配置视频片段的语义分类型，用于自动分析组织视频内容。")
    
    # 加载当前定义
    current_definitions = load_semantic_definitions()
    
    # 创建编辑状态
    if "semantic_definitions_editing" not in st.session_state:
        st.session_state.semantic_definitions_editing = copy.deepcopy(current_definitions)
    
    # 重置按钮
    col1, col2, col3 = st.columns([1, 1, 2])
    
    with col1:
        if st.button("🔄 重置为默认", help="恢复到系统默认的语义类型定义"):
            st.session_state.semantic_definitions_editing = copy.deepcopy(DEFAULT_SEMANTIC_TYPE_DEFINITIONS)
            st.rerun()
    
    with col2:
        if st.button("💾 保存配置", help="保存当前的语义类型定义"):
            if save_semantic_definitions(st.session_state.semantic_definitions_editing):
                st.success("✅ 语义类型定义已保存！")
                st.balloons()
            else:
                st.error("❌ 保存失败，请重试。")
    
    st.markdown("---")
    
    # 语义类型列表
    st.markdown("#### 📋 当前语义类型")
    
    # 显示效果预览
    with st.expander("📊 预览效果", expanded=False):
        st.markdown("视频片段将按以下类型进行分析：")
        for type_name in DEFAULT_SEMANTIC_SEGMENT_TYPES:
            definition = st.session_state.semantic_definitions_editing.get(type_name, {})
            st.markdown(f"- **{type_name}**: {definition.get('description', '未定义')[:50]}...")
    
    # 编辑界面
    st.markdown("#### ✏️ 编辑语义类型定义")
    
    # 类型选择
    selected_type = st.selectbox(
        "选择要编辑的语义类型：",
        options=DEFAULT_SEMANTIC_SEGMENT_TYPES,
        help="选择要修改定义的语义类型"
    )
    
    if selected_type:
        # 获取当前定义
        current_def = st.session_state.semantic_definitions_editing.get(selected_type, {
            "name": selected_type,
            "description": "",
            "keywords": [],
            "examples": []
        })
        
        # 编辑表单
        with st.form(f"edit_semantic_type_{selected_type}"):
            st.markdown(f"##### 🎯 编辑「{selected_type}」")
            
            # 类型名称（只读显示）
            st.text_input("类型名称", value=current_def.get("name", selected_type), disabled=True)
            
            # 描述
            description = st.text_area(
                "详细描述",
                value=current_def.get("description", ""),
                height=120,
                help="详细描述该语义类型的特征、用途和识别要点",
                placeholder="例如：视频的起始部分，用于吸引观众、引入品牌或奠定视频基调..."
            )
            
            # 关键词
            keywords_text = st.text_area(
                "关键词列表（每行一个）",
                value="\n".join(current_def.get("keywords", [])),
                height=80,
                help="输入用于识别该类型的关键词，每行一个",
                placeholder="开场白\n品牌介绍\nslogan"
            )
            
            # 示例
            examples_text = st.text_area(
                "示例文本（每行一个典型表达模式）",
                value="\n".join(current_def.get("examples", [])),
                height=100,
                help="输入典型的表达模式，每行一个独立的表达方式，不要输入连贯的段落",
                placeholder="大家好，我是xxx\n今天要给大家介绍\n启赋奶粉带来\n欢迎大家关注\n感谢观看"
            )
            
            # 🆕 添加示例说明
            st.info("""
            💡 **示例文本最佳实践**：
            
            ✅ **推荐做法**（每行一种表达模式）：
            ```
            大家好，我是xxx
            今天要给大家介绍  
            启赋奶粉带来
            欢迎观看今天的视频
            感谢大家的关注
            ```
            
            ❌ **不推荐**（连贯段落）：
            ```
            大家好，我是xxx。今天要给大家介绍启赋奶粉带来的营养价值，欢迎观看今天的视频，感谢大家的关注。
            ```
            
            **原因**：每行代表一种典型表达模式，让LLM能学习到多种不同的表达方式，提高识别准确性。
            """)
            
            # 保存按钮
            col1, col2 = st.columns([1, 3])
            with col1:
                submitted = st.form_submit_button("💾 保存修改", use_container_width=True)
            
            if submitted:
                # 处理关键词和示例
                keywords = [kw.strip() for kw in keywords_text.split("\n") if kw.strip()]
                examples = [ex.strip() for ex in examples_text.split("\n") if ex.strip()]
                
                # 更新定义
                st.session_state.semantic_definitions_editing[selected_type] = {
                    "name": selected_type,
                    "description": description.strip(),
                    "keywords": keywords,
                    "examples": examples
                }
                
                st.success(f"✅ 「{selected_type}」定义已更新！记得点击上方的「💾 保存配置」按钮持久化保存。")
                st.rerun()
        
        # 显示当前定义预览
        with st.expander(f"📖 「{selected_type}」当前定义预览", expanded=True):
            def_preview = st.session_state.semantic_definitions_editing.get(selected_type, {})
            
            st.markdown(f"**描述**: {def_preview.get('description', '未定义')}")
            
            if def_preview.get('keywords'):
                st.markdown(f"**关键词**: {', '.join(def_preview['keywords'])}")
            
            if def_preview.get('examples'):
                st.markdown("**示例**:")
                for example in def_preview['examples']:
                    st.markdown(f"- {example}")

def render_semantic_type_quick_actions():
    """渲染快速操作面板"""
    st.markdown("#### ⚡ 快速操作")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📥 导入配置", help="从JSON文件导入语义类型定义"):
            uploaded_file = st.file_uploader(
                "选择配置文件",
                type=["json"],
                key="semantic_import"
            )
            if uploaded_file:
                try:
                    imported_config = json.load(uploaded_file)
                    if "SEMANTIC_TYPE_DEFINITIONS" in imported_config:
                        st.session_state.semantic_definitions_editing = imported_config["SEMANTIC_TYPE_DEFINITIONS"]
                        st.success("✅ 配置导入成功！")
                    else:
                        st.error("❌ 文件格式不正确")
                except Exception as e:
                    st.error(f"❌ 导入失败: {e}")
    
    with col2:
        if st.button("📤 导出配置", help="导出当前语义类型定义"):
            export_data = {
                "SEMANTIC_TYPE_DEFINITIONS": st.session_state.get("semantic_definitions_editing", current_definitions)
            }
            st.download_button(
                label="下载配置文件",
                data=json.dumps(export_data, ensure_ascii=False, indent=2),
                file_name="semantic_type_definitions.json",
                mime="application/json"
            )
    
    with col3:
        if st.button("🔍 验证配置", help="检查当前配置的完整性"):
            editing_defs = st.session_state.get("semantic_definitions_editing", {})
            missing_types = []
            
            for type_name in DEFAULT_SEMANTIC_SEGMENT_TYPES:
                if type_name not in editing_defs or not editing_defs[type_name].get("description"):
                    missing_types.append(type_name)
            
            if missing_types:
                st.warning(f"⚠️ 以下类型缺少详细定义: {', '.join(missing_types)}")
            else:
                st.success("✅ 所有语义类型都已配置完整！") 