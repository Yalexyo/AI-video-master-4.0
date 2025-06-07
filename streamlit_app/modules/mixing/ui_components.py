"""
混剪工厂UI组件模块
提取和封装用户界面组件，保持代码模块化
"""

import streamlit as st
import os
from typing import Dict, List, Any
from pathlib import Path

# 导入配置和工具
from streamlit_app.config.mixing_config import MixingConfig
from streamlit_app.utils.mixing.srt_utils import (
    calculate_srt_annotated_duration
)
from streamlit_app.utils.path_utils import get_video_pool_path, ensure_path_exists, get_google_video_path, get_output_path


def render_quality_settings() -> Dict[str, Any]:
    """渲染画质设置组件
    
    Returns:
        Dict: 包含分辨率、比特率、帧率的设置字典
    """
    st.subheader("🎥 输出设置")
    
    # 使用配置中的预设
    quality_presets = MixingConfig.QUALITY_PRESETS
    
    preset = st.selectbox("画质预设", list(quality_presets.keys()), key="mixing_quality_preset")
    preset_values = quality_presets[preset]
    
    # 默认使用预设值
    settings = {
        "resolution": preset_values["resolution"],
        "bitrate": preset_values["bitrate"],
        "fps": preset_values["fps"]
    }
    
    # 允许微调
    enable_custom = st.checkbox("🔧 启用画质微调", value=False, key="mixing_enable_custom_quality")
    if enable_custom:
        settings["resolution"] = st.text_input(
            "分辨率", 
            value=preset_values["resolution"],
            help="格式: 宽x高，如 1920x1080",
            key="mixing_custom_resolution"
        )
        settings["bitrate"] = st.text_input(
            "比特率", 
            value=preset_values["bitrate"],
            help="格式: 数值k，如 5000k",
            key="mixing_custom_bitrate"
        )
        settings["fps"] = st.number_input(
            "帧率", 
            min_value=15, 
            max_value=60, 
            value=preset_values["fps"],
            key="mixing_custom_fps"
        )
    
    return settings


def render_strategy_selection() -> str:
    """渲染策略选择组件
    
    Returns:
        str: 选择的策略名称
    """
    st.markdown("### 🎯 **步骤1: 选择片段匹配策略**")
    
    # 策略选择界面
    strategy_col1, strategy_col2 = st.columns([1, 1])
    
    with strategy_col1:
        st.markdown("#### 📋 **SRT标注模式**")
        st.info("✅ **适合**: 有清晰的SRT标注，希望精准控制")
        st.markdown("""
        **特点**:
        - 🎯 严格按照您的手动标注进行片段匹配
        - 📊 自动根据SRT标注时长计算比例
        - 🚫 不使用任何算法优化
        - ⚡ 结果完全可预期和可控制
        """)
        
        manual_selected = st.button(
            "📋 选择SRT标注模式", 
            type="primary" if st.session_state.get('selection_strategy') == 'manual_annotation' else "secondary",
            use_container_width=True,
            key="select_manual_strategy"
        )
        
        if manual_selected:
            st.session_state.selection_strategy = 'manual_annotation'
            st.rerun()
    
    with strategy_col2:
        st.markdown("#### 🤖 **算法优化模式**")
        st.info("✅ **适合**: 希望AI自动优化，获得最佳组合")
        st.markdown("""
        **特点**:
        - 🧠 使用复杂算法进行智能片段选择
        - ⚙️ 手动设置各模块时长比例
        - 🎯 多维度优化（质量、多样性、时长）
        - 🔄 支持智能降级确保成功率
        """)
        
        traditional_selected = st.button(
            "🤖 选择算法优化模式", 
            type="primary" if st.session_state.get('selection_strategy') == 'traditional' else "secondary",
            use_container_width=True,
            key="select_traditional_strategy"
        )
        
        if traditional_selected:
            st.session_state.selection_strategy = 'traditional'
            st.rerun()
    
    # 显示当前选择的策略
    current_strategy = st.session_state.get('selection_strategy', None)
    if current_strategy:
        if current_strategy == 'manual_annotation':
            st.success("📋 **已选择**: SRT标注模式 - 基于手动标注的精准匹配")
        else:
            st.success("🤖 **已选择**: 算法优化模式 - 基于AI算法的智能优化")
        return current_strategy
    else:
        st.warning("⚠️ **请先选择一种片段匹配策略**")
        return ""


def render_duration_ratio_config() -> Dict[str, float]:
    """渲染时长比例配置组件
    
    Returns:
        Dict: 各模块的时长比例
    """
    st.markdown("**各模块时长占比:**")
    
    # 使用配置中的模板
    templates = MixingConfig.DURATION_RATIO_TEMPLATES
    
    template_choice = st.selectbox("选择预设模板", list(templates.keys()), key="mixing_ratio_template")
    template_ratios = templates[template_choice]
    
    # 默认使用模板值
    ratios = template_ratios.copy()
    
    # 允许微调比例
    enable_custom_ratios = st.checkbox("🎛️ 启用自定义比例", value=False, key="mixing_enable_custom_ratios")
    if enable_custom_ratios:
        pain_ratio = st.slider("痛点", 0.0, 1.0, template_ratios["痛点"], 0.05, key="mixing_pain_ratio")
        solution_ratio = st.slider("解决方案", 0.0, 1.0, template_ratios["解决方案"], 0.05, key="mixing_solution_ratio")
        selling_ratio = st.slider("卖点", 0.0, 1.0, template_ratios["卖点"], 0.05, key="mixing_selling_ratio")
        promo_ratio = st.slider("促销", 0.0, 1.0, template_ratios["促销"], 0.05, key="mixing_promo_ratio")
        
        # 归一化处理
        total = pain_ratio + solution_ratio + selling_ratio + promo_ratio
        if total > 0:
            ratios = {
                "痛点": pain_ratio / total,
                "解决方案": solution_ratio / total,
                "卖点": selling_ratio / total,
                "促销": promo_ratio / total
            }
        else:
            ratios = template_ratios
        
        # 显示归一化后的比例
        st.markdown("**归一化后的比例:**")
        for category, ratio in ratios.items():
            st.text(f"{category}: {ratio:.1%}")
    
    return ratios


def render_sidebar_config() -> Dict[str, Any]:
    """渲染侧边栏配置组件
    
    Returns:
        Dict: 配置参数字典
    """
    with st.sidebar:
        st.subheader("📁 数据源配置")
        
        # 使用统一的路径工具
        video_pool_path = get_video_pool_path()
        video_pool_path_str = str(video_pool_path)
        
        # 显示目录信息
        st.markdown(f"**📂 映射路径**: `{video_pool_path_str}`")
        
        # 确保目录存在
        ensure_path_exists(video_pool_path)
        
        # 检查路径是否存在
        path_exists = video_pool_path.exists()
        if path_exists:
            json_files = [f for f in video_pool_path.iterdir() if f.suffix == '.json']
            json_file_names = [f.name for f in json_files]
            st.success(f"✅ 目录存在，发现 {len(json_files)} 个JSON文件")
            
            # 显示文件详情
            if json_files:
                with st.expander("📄 文件详情", expanded=False):
                    for i, file in enumerate(json_file_names[:10], 1):  # 最多显示10个文件
                        st.text(f"{i}. {file}")
                    if len(json_files) > 10:
                        st.text(f"... 还有 {len(json_files) - 10} 个文件")
        else:
            st.error(f"❌ 目录不存在: {video_pool_path_str}")
            json_file_names = []
        
        # 映射配置
        st.subheader("⚙️ 映射配置")
        
        use_deepseek = st.checkbox(
            "启用DeepSeek模型兜底",
            value=MixingConfig.DEEPSEEK_ENABLED,
            help="当关键词规则无法分类时，使用DeepSeek模型进行智能分类",
            key="mixing_use_deepseek"
        )
        
        clear_cache = st.button(
            "🗑️ 清除缓存",
            help="清除映射结果缓存，强制重新处理",
            key="mixing_clear_cache"
        )
        
        if clear_cache:
            st.cache_data.clear()
            st.success("缓存已清除")
    
    return {
        "video_pool_path": video_pool_path_str,
        "path_exists": path_exists and bool(json_file_names),  # 只有当存在JSON文件时才认为路径有效
        "use_deepseek": use_deepseek,
        "json_files": json_file_names,
        "selected_subdir": None
    }


def render_file_management() -> None:
    """渲染文件管理组件"""
    st.markdown("#### 📁 文件管理")
    
    # 创建目录按钮
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📁 创建google_video目录", help="创建Google Video分析结果目录", key="mixing_create_google_video"):
            try:
                google_video_path = get_google_video_path()
                if ensure_path_exists(google_video_path):
                    st.success(f"✅ 目录已创建: {google_video_path}")
                    st.info("💡 现在您可以将视频分析结果保存到此目录中")
                else:
                    st.error("❌ 创建目录失败")
                st.rerun()
            except Exception as e:
                st.error(f"❌ 创建目录失败: {e}")
    
    with col2:
        if st.button("📁 创建输出目录", help="确保输出目录存在", key="mixing_create_output"):
            try:
                output_path = get_output_path()
                if ensure_path_exists(output_path):
                    st.success(f"✅ 目录已创建: {output_path}")
                else:
                    st.error("❌ 创建目录失败")
            except Exception as e:
                st.error(f"❌ 创建目录失败: {e}")


def render_progress_display(current: int, total: int, message: str = "") -> None:
    """渲染进度显示组件
    
    Args:
        current: 当前进度
        total: 总数
        message: 进度消息
    """
    if total > 0:
        progress = current / total
        st.progress(progress, text=f"{message} ({current}/{total})")
    else:
        st.progress(0, text=message)


def render_mapping_statistics(statistics: Dict[str, Any]) -> None:
    """渲染映射统计信息
    
    Args:
        statistics: 映射统计信息字典
    """
    if not statistics:
        return
    
    st.subheader("📊 映射统计")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_segments = statistics.get("total_segments", 0)
        st.metric("总片段数", total_segments)
    
    with col2:
        categorized = statistics.get("categorized_segments", 0)
        st.metric("已分类片段", categorized)
    
    with col3:
        avg_quality = statistics.get("avg_quality_score", 0)
        st.metric("平均质量分", f"{avg_quality:.2f}")
    
    with col4:
        total_duration = statistics.get("total_duration", 0)
        st.metric("总时长", f"{total_duration:.1f}s")
    
    # 类别分布
    category_stats = statistics.get("category_distribution", {})
    if category_stats:
        st.markdown("**📊 类别分布**")
        
        for category, count in category_stats.items():
            percentage = (count / total_segments * 100) if total_segments > 0 else 0
            st.progress(percentage / 100, text=f"{category}: {count} ({percentage:.1f}%)")


def display_srt_based_ratios(srt_entries: List[Dict], srt_annotations: Dict) -> None:
    """显示基于SRT标注的时长比例
    
    Args:
        srt_entries: SRT条目列表
        srt_annotations: SRT标注字典
    """
    # 计算标注时长分布
    annotated_durations = {"痛点": 0, "解决方案": 0, "卖点": 0, "促销": 0}
    total_duration = 0
    
    for entry in srt_entries:
        entry_index = entry['index']
        annotation = None
        
        # 处理多种标注数据格式
        if entry_index in srt_annotations:
            annotation = srt_annotations[entry_index]
        
        srt_key = f"srt_{entry_index}"
        if srt_key in srt_annotations:
            annotation_data = srt_annotations[srt_key]
            if isinstance(annotation_data, dict):
                annotation = annotation_data.get('module')
            else:
                annotation = annotation_data
        
        # 只计算已标注且不为"未标注"的条目
        if annotation and annotation != '未标注':
            if 'start_time' in entry and 'end_time' in entry:
                duration = entry['end_time'] - entry['start_time']
            else:
                from streamlit_app.utils.mixing.srt_utils import parse_srt_timestamp_duration
                timestamp = entry.get('timestamp', '')
                duration = parse_srt_timestamp_duration(timestamp)
            
            if annotation in annotated_durations:
                annotated_durations[annotation] += duration
            total_duration += duration
    
    if total_duration > 0:
        st.markdown("**📊 基于SRT标注的时长分布:**")
        
        ratios = {}
        for category, duration in annotated_durations.items():
            ratio = duration / total_duration
            ratios[category] = ratio
            
            # 显示比例
            col1, col2 = st.columns([3, 1])
            with col1:
                st.progress(ratio, text=f"{category}: {ratio:.1%}")
            with col2:
                st.text(f"{duration:.1f}s")
        
        # 保存到session state
        st.session_state.target_ratios = ratios
        
        # 显示总时长信息
        st.info(f"✅ **已标注总时长**: {total_duration:.1f}秒 | 这将作为视频合成的目标时长基准")
        
    else:
        st.warning("⚠️ 未找到有效的SRT标注数据") 