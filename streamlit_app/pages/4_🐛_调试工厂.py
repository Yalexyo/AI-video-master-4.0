import streamlit as st
import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
import pandas as pd
import sys
from pathlib import Path
import yaml
import time
from copy import deepcopy

from utils.config_manager import get_config_manager, CONFIG_PATH

# 添加项目根目录到Python路径
current_dir = Path(__file__).parent.absolute()
project_root = current_dir.parent.parent
sys.path.insert(0, str(project_root))

# 设置日志
logger = logging.getLogger(__name__)

# 页面配置
st.set_page_config(
    page_title="🐛 调试工厂 - AI视频混剪系统",
    page_icon="🐛",
    layout="wide"
)

def main():
    """调试工厂主界面"""
    
    st.title("🐛 调试工厂")
    st.markdown("**实时查看映射机制、过滤规则和选片过程的详细信息**")
    
    # 侧边栏 - 调试选项
    with st.sidebar:
        st.header("🔧 调试选项")
        
        # 只保留两个调试模式
        debug_mode = st.selectbox(
            "选择调试模式",
            ["适配分类机制", "词汇管理中心"],
            index=0,
            help="选择要使用的调试功能"
        )
        
        st.markdown("---")
        
        if debug_mode == "适配分类机制":
            st.info("🔧 当前模式：适配分类机制")
        elif debug_mode == "词汇管理中心":
            st.info("📚 当前模式：词汇管理中心")
    
    # 主要内容区域
    if debug_mode == "适配分类机制":
        render_debug_classification()
    elif debug_mode == "词汇管理中心":
        render_vocabulary_management()

def render_debug_classification():
    """渲染调试分类机制界面"""
    st.header("🔧 适配分类机制")
    st.markdown("**按模块分类片段并保存到对应文件夹，便于调试映射机制是否正确**")
    
    # 检查必要的session state数据
    mapped_segments = st.session_state.get('mapped_segments', [])
    srt_entries = st.session_state.get('srt_entries', [])
    
    # 🔧 NEW: 添加独立的片段扫描功能
    col_scan, col_status = st.columns([1, 2])
    
    with col_scan:
        if st.button("🔄 重新扫描片段", help="独立扫描video_pool目录，获取最新的片段数据"):
            try:
                from modules.mapper import get_cached_mapping_results, resolve_video_pool_path
                
                # 强制清除相关缓存
                st.cache_data.clear()
                
                # 🔧 使用跨平台兼容的路径解析
                video_pool_path = "data/output/google_video/video_pool"
                resolved_path = resolve_video_pool_path(video_pool_path)
                
                with st.spinner("🔄 正在扫描video_pool目录..."):
                    logger.info(f"🔄 开始重新扫描片段，路径: {resolved_path}")
                    
                    # 调用映射函数获取最新数据
                    mapped_segments, stats = get_cached_mapping_results(resolved_path)
                    
                    # 更新session state
                    st.session_state.mapped_segments = mapped_segments
                    st.session_state.mapping_stats = stats
                    
                    logger.info(f"✅ 重新扫描完成，加载了 {len(mapped_segments)} 个片段")
                    
                    st.success(f"🎉 扫描完成！发现 {len(mapped_segments)} 个片段")
                    
                    # 显示扫描统计
                    if stats and stats.get("by_video"):
                        st.info(f"📊 按视频分布: {dict(list(stats['by_video'].items())[:5])}")
                    
                    # 强制刷新页面
                    st.rerun()
                    
            except Exception as e:
                logger.error(f"重新扫描失败: {e}")
                st.error(f"❌ 扫描失败: {e}")
    
    with col_status:
        # 显示当前状态
        total_segments = len(mapped_segments)
        if total_segments > 0:
            st.success(f"✅ 已加载映射片段: {total_segments} 个")
            
            # 显示视频分布
            if mapped_segments:
                video_distribution = {}
                for segment in mapped_segments:
                    video_id = segment.get('video_id', 'unknown')
                    video_distribution[video_id] = video_distribution.get(video_id, 0) + 1
                
                if len(video_distribution) > 1:
                    st.info(f"📊 视频分布: {dict(list(video_distribution.items())[:3])}{'...' if len(video_distribution) > 3 else ''}")
        else:
            st.warning("⚠️ 未检测到映射片段数据")
            st.info("💡 请点击上方的「重新扫描片段」按钮获取最新数据")
    
    # SRT数据状态检查
    col1, col2 = st.columns(2)
    with col2:
        if srt_entries:
            st.success(f"✅ 已加载SRT数据: {len(srt_entries)} 条")
        else:
            st.warning("⚠️ 未检测到SRT时间参考数据")
    
    # 功能说明
    st.info("""
    🎯 **功能说明**:
    1. 根据SRT时间比例和映射机制对所有片段进行分类
    2. 将片段按模块保存到【痛点】【解决方案】【卖点】【促销】文件夹中
    3. 生成详细的分类统计报告，便于调试和优化
    """)
    
    # 执行按钮
    debug_disabled = not (mapped_segments and srt_entries)
    
    if st.button("🔧 执行调试分类", 
                disabled=debug_disabled, 
                type="primary",
                help="将所有片段按模块分类并保存到对应文件夹"):
        
        if debug_disabled:
            st.error("❌ 需要先扫描片段数据并加载SRT文件")
            return
            
        execute_debug_classification(mapped_segments, srt_entries)
    
    if debug_disabled:
        st.markdown("---")
        st.info("""
        📋 **使用步骤**:
        1. 点击上方「重新扫描片段」按钮加载最新数据
        2. 前往 🧪 混剪工厂 加载标杆视频SRT文件
        3. 返回此处执行调试分类
        """)
    
    # 🔧 NEW: 显示当前状态汇总
    if mapped_segments or srt_entries:
        st.markdown("---")
        st.markdown("### 📊 当前状态汇总")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("映射片段", len(mapped_segments))
        with col2:
            st.metric("SRT条目", len(srt_entries))
        with col3:
            ready_status = "✅ 就绪" if (mapped_segments and srt_entries) else "⚠️ 未就绪"
            st.metric("调试状态", ready_status)

def apply_global_filters(segments: List[Dict]) -> List[Dict]:
    """应用全局排除过滤规则"""
    
    # 🔧 使用ConfigManager替代直接读取matching_rules.json
    try:
        from utils.config_manager import get_config_manager
        config_manager = get_config_manager()
        raw_config = config_manager.get_raw_config()
        
        # 从统一配置中提取全局设置
        global_settings = raw_config.get("global_settings", {})
        global_exclude_keywords = global_settings.get("global_exclusion_keywords", [])
        max_segments_per_module = global_settings.get("max_segments_per_module", 3)
        max_duration = global_settings.get("max_duration_seconds", 10)
        
        logger.info(f"✅ 成功从ConfigManager加载全局设置")
        
    except Exception as e:
        logger.warning(f"无法从ConfigManager加载全局设置，使用默认值: {e}")
        global_exclude_keywords = ["疑似", "模糊", "不清楚"]
        max_segments_per_module = 3
        max_duration = 10
    
    # 质量阈值 
    min_quality_threshold = 0.3
    
    filtered_segments = []
    
    for segment in segments:
        # 检查时长
        duration = segment.get('duration', 0)
        if duration > max_duration:
            logger.info(f"🕒 时长过滤: {segment.get('file_name', '')} (时长{duration:.1f}s > 限制{max_duration}s)")
            continue
            
        # 检查质量分数
        quality = segment.get('combined_quality', 0)
        if quality < min_quality_threshold:
            logger.info(f"📊 质量过滤: {segment.get('file_name', '')} (质量{quality:.2f} < 阈值{min_quality_threshold})")
            continue
            
        # 检查全局排除关键词
        all_tags = segment.get('all_tags', [])
        transcription = segment.get('transcription', '')
        
        excluded = False
        excluding_keywords = []
        
        for keyword in global_exclude_keywords:
            # 检查标签 - 增加类型安全检查
            for tag in all_tags:
                if tag is None:
                    continue
                tag_str = tag if isinstance(tag, str) else str(tag)
                if keyword and isinstance(keyword, str) and keyword.lower() in tag_str.lower():
                    excluded = True
                    excluding_keywords.append(keyword)
                    break
            
            # 检查转录文本 - 增加类型安全检查
            if transcription is not None and isinstance(transcription, str) and keyword and isinstance(keyword, str):
                if keyword.lower() in transcription.lower():
                    excluded = True
                    excluding_keywords.append(keyword)
                        
        if excluded:
            logger.info(f"🚫 关键词排除: {segment.get('file_name', '')} (关键词: {excluding_keywords})")
            continue
        
        # 通过所有过滤器
        filtered_segments.append(segment)
    
    return filtered_segments

def limit_segments_per_module(classification_result: Dict, max_per_module: int = None) -> Dict:
    """限制每个模块的片段数量"""
    
    # 如果没有传入限制数量，从ConfigManager读取
    if max_per_module is None:
        try:
            from utils.config_manager import get_config_manager
            config_manager = get_config_manager()
            raw_config = config_manager.get_raw_config()
            max_per_module = raw_config.get("global_settings", {}).get("max_segments_per_module", 3)
        except Exception as e:
            logger.warning(f"无法从ConfigManager读取模块数量限制，使用默认值3: {e}")
            max_per_module = 3
    
    for module_name, stats in classification_result.get("module_stats", {}).items():
        if stats["saved_segments"] > max_per_module:
            st.warning(f"⚠️ 模块 '{module_name}' 有 {stats['saved_segments']} 个片段，超过限制 {max_per_module} 个")
            st.info(f"💡 建议：调整关键词匹配规则或提高质量阈值来减少片段数量")
    
    return classification_result

def execute_debug_classification(mapped_segments: List[Dict], srt_entries: List[Dict]):
    """执行调试分类：按模块分类片段并保存到对应文件夹"""
    try:
        # 导入调试分类器
        from modules.debug_classifier import DebugClassifier
        
        # 从图片显示的比例计算目标比例
        target_ratios = [25, 21, 49, 4]  # 痛点, 解决方案, 卖点, 促销 (根据用户图片)
        
        # 🆕 添加全局排除过滤
        st.markdown("### 🚫 应用全局排除规则")
        
        # 预过滤片段
        filtered_segments = apply_global_filters(mapped_segments)
        
        # 显示过滤统计
        original_count = len(mapped_segments)
        filtered_count = len(filtered_segments)
        excluded_count = original_count - filtered_count
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("原始片段", original_count)
        with col2:
            st.metric("通过过滤", filtered_count)
        with col3:
            st.metric("被排除", excluded_count, delta=f"-{excluded_count}")
        
        if excluded_count > 0:
            st.warning(f"⚠️ 有 {excluded_count} 个片段被全局排除规则过滤")
        
        with st.spinner("🔧 正在按模块分类片段..."):
            # 创建调试分类器
            debug_classifier = DebugClassifier()
        
            # 执行分类（使用过滤后的片段）
            classification_result = debug_classifier.classify_and_save_segments_by_srt_timing(
                mapped_segments=filtered_segments,
                srt_entries=srt_entries,
                target_ratios=target_ratios
            )
            
            # 显示分类结果
            st.success("✅ 调试分类完成！")
        
            # 🆕 检查模块数量限制
            classification_result = limit_segments_per_module(classification_result)
            
            # 展示统计结果
            st.markdown("### 📊 分类统计结果")
            col1, col2, col3 = st.columns(3)
    
            with col1:
                st.metric("原始总数", original_count)
    
            with col2:
                st.metric("过滤后数", filtered_count)
    
            with col3:
                st.metric("最终分类", classification_result["classified_segments"])
    
            # 分类成功率
            success_rate = (classification_result["classified_segments"] / 
                          max(filtered_count, 1)) * 100
            st.metric("分类成功率", f"{success_rate:.1f}%", 
                     help="基于过滤后片段的分类成功率")
            
            # 各模块详细统计
            st.markdown("#### 📁 各模块分类结果")
            
            for module_name, stats in classification_result["module_stats"].items():
                folder_name = debug_classifier.module_folders.get(module_name, module_name)
                
                col1, col2, col3, col4 = st.columns(4)
    
                with col1:
                    st.markdown(f"**📁 {folder_name}**")
    
                with col2:
                    st.metric("片段数", stats["saved_segments"])
                
                with col3:
                    st.metric("实际时长", f"{stats['actual_time']:.1f}s")
                
                with col4:
                    st.metric("目标时长", f"{stats['target_time']:.1f}s")
                
                # 显示文件夹路径
                st.code(stats["folder_path"], language=None)
            
            # 显示SRT时间分配
            st.markdown("### ⏱️ SRT时间分配参考")
            st.markdown("#### 📊 基于SRT的模块时间分配")
            
            for module, time_range in classification_result["srt_time_ranges"].items():
                folder_name = debug_classifier.module_folders.get(module, module)
                st.markdown(
                    f"**{folder_name}**: {time_range['start']:.1f}s - {time_range['end']:.1f}s "
                    f"(时长: {time_range['duration']:.1f}s, 比例: {time_range['ratio']}%)"
                )
            
            # 显示全局排除详情
            if excluded_count > 0:
                st.markdown("### 🚫 全局排除详情")
                with st.expander(f"查看被排除的 {excluded_count} 个片段", expanded=False):
                    excluded_segments = [seg for seg in mapped_segments if seg not in filtered_segments]
                    
                    for i, segment in enumerate(excluded_segments[:10]):  # 只显示前10个
                        col1, col2 = st.columns([2, 3])
                        
                        with col1:
                            st.write(f"**{segment.get('file_name', 'Unknown')}**")
                            st.write(f"时长: {segment.get('duration', 0):.1f}s")
                            st.write(f"质量: {segment.get('combined_quality', 0):.2f}")
                        
                        with col2:
                            tags = segment.get('all_tags', [])
                            if tags:
                                st.write(f"标签: {', '.join(tags[:3])}{'...' if len(tags) > 3 else ''}")
                            transcription = segment.get('transcription', '')
                            if transcription:
                                st.write(f"转录: {transcription[:50]}{'...' if len(transcription) > 50 else ''}")
                
                    if len(excluded_segments) > 10:
                        st.info(f"还有 {len(excluded_segments) - 10} 个片段未显示...")
            
            st.markdown("---")
            
            # 下一步建议
            st.info("""
            🎯 **调试建议**:
            1. 检查各文件夹中的视频片段是否符合预期模块类型
            2. 查看片段信息JSON文件了解分类原因
            3. 如发现分类错误，可调整配置文件中的关键词
            4. 如果某个模块片段过多，考虑提高该模块的质量阈值
            5. 检查全局排除规则是否过于严格
            6. 重新运行调试分类验证优化效果
            """)
            
    except ImportError:
        st.error("❌ 调试分类器模块导入失败，请检查代码")
    except Exception as e:
        logger.error(f"调试分类执行失败: {e}")
        st.error(f"❌ 调试分类失败: {e}")

def auto_save_config(config, save_msg_container=None):
    """自动保存配置并显示成功提醒"""
    try:
        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, allow_unicode=True, sort_keys=False, indent=2)
        
        if save_msg_container:
            with save_msg_container:
                st.success("✅ 保存成功！", icon="✅")
        
        # 清除缓存
        st.cache_data.clear()
        st.cache_resource.clear()
        
        return True
    except Exception as e:
        if save_msg_container:
            with save_msg_container:
                st.error(f"❌ 保存失败: {e}")
        return False

def handle_input_change(config, module_key, save_container):
    """处理输入变更的即时保存"""
    auto_save_config(config, save_container)

def create_input_change_callback(config, module_key, save_container):
    """创建输入变更回调函数"""
    def callback():
        auto_save_config(config, save_container)
    return callback

def handle_delete_item(config, module_key, category, index, save_container):
    """处理删除项目的即时保存"""
    try:
        if "ai_batch" in config[module_key] and category in config[module_key]["ai_batch"]:
            items = config[module_key]["ai_batch"][category]
            if 0 <= index < len(items):
                items.pop(index)
                auto_save_config(config, save_container)
    except Exception as e:
        st.error(f"删除失败: {e}")

def handle_add_item(config, module_key, category, save_container):
    """处理添加项目的即时保存"""
    try:
        if "ai_batch" not in config[module_key]:
            config[module_key]["ai_batch"] = {}
        if category not in config[module_key]["ai_batch"]:
            config[module_key]["ai_batch"][category] = []
        
        config[module_key]["ai_batch"][category].append({"word": "", "weight": 2})
        auto_save_config(config, save_container)
    except Exception as e:
        st.error(f"添加失败: {e}")

def render_vocabulary_management():
    """📚 词汇管理：编辑业务蓝图，动态生成AI配置"""
    st.subheader("📚 词汇管理 - 业务蓝图编辑器")
    
    # 🆕 显示当前配置模式和统计
    st.markdown("### 📊 当前配置状态")
    
    try:
        config_manager = get_config_manager()
        vocab = config_manager.get_ai_vocabulary()
        stats = config_manager.get_ai_statistics()
        supports_batch = config_manager.supports_batch_definition()
        
        col1, col2, col3 = st.columns([1, 1, 1])
        
        with col1:
            mode_color = "🟢" if supports_batch else "🟡"
            mode_text = "批量定义模式" if supports_batch else "传统映射模式"
            st.metric("配置模式", mode_text, delta=mode_color)
        
        with col2:
            total_words = sum(stats.values())
            st.metric("总词汇数", total_words)
        
        col_stat = st.columns(4)
        total_words = sum(stats.values())
        categories = ["object", "scene", "emotion", "brand"]
        category_names = ["Object", "Scene", "Emotion", "Brand"]
        category_colors = ["🎯", "🏞️", "💭", "🏷️"]
        for i, (cat, name, color) in enumerate(zip(categories, category_names, category_colors)):
            with col_stat[i]:
                ratio = stats[cat] / total_words * 100 if total_words > 0 else 0
                # 业务建议：场景<20%显示🎯优化目标，其它类别<20%显示⚠️建议补充
                if cat == "scene":
                    delta = "🎯 优化目标" if ratio < 20 else "✅ 良好"
                else:
                    delta = "⚠️ 建议补充" if ratio < 20 else "✅ 良好"
                st.metric(f"{color} {name} 占比", f"{ratio:.1f}%", delta=delta)
        # 保留原有分布详情
        st.markdown("**AI词汇分布详情:**")
        distribution_cols = st.columns(4)
        for i, (category, color) in enumerate(zip(categories, category_colors)):
            with distribution_cols[i]:
                count = stats[category]
                st.metric(f"{color} {category_names[i]}", count)
        
        if supports_batch:
            st.success("✅ **正在使用批量定义**: 您可以精确控制每个词汇的AI类别归属")
        else:
            st.warning("⚠️ **正在使用传统映射**: 系统按预设规则自动分配AI类别")
        
        st.markdown("---")
        
    except Exception as e:
        st.error(f"❌ 获取配置状态失败: {e}")
    
    st.markdown("""
    🎯 **单一数据源**: 这里是业务逻辑的唯一真实来源。
    - **您编辑的是**: `keywords.yml` 文件中的业务概念。
    - **系统自动处理**: 根据您的定义，动态生成AI词汇表和分类规则。
    - **一处修改，全局生效**: 修改并保存后，整个系统将立即采用新规则。

    ### 🆕 配置方式说明

    **🔹 批量定义 (ai_batch)** - 推荐使用
    - ✅ **精确控制**: 直接指定每个词汇属于哪个AI类别
    - ✅ **灵活映射**: 不受传统业务概念限制
    - ✅ **优化分布**: 可以手动平衡各AI类别的词汇数量
    """)

    try:
        config_manager = get_config_manager()
        config = config_manager.get_raw_config()
        if not config:
            st.error("❌ 无法加载业务蓝图 (keywords.yml)，请检查文件是否存在或格式是否正确。")
            return
    except Exception as e:
        st.error(f"❌ 加载配置时出错: {e}")
        return

    # 初始化 session_state
    if 'vocab_config' not in st.session_state:
        st.session_state['vocab_config'] = deepcopy(config)
    vocab_config = st.session_state['vocab_config']

    # --- 模块化编辑界面 ---
    
    # 🎭 首先显示 Shared 模块 (统一配置)
    with st.expander("🎭 Shared模块：情绪词库配置 (视觉+音频AI共用)", expanded=True):
        shared_data = vocab_config.get("shared", {})
        st.markdown("### 🌐 统一情绪配置")
        st.info("**说明**: 这些情绪词汇将被所有AI模型共享使用，包括Qwen视觉分析和DeepSeek音频分析")
        
        ai_batch = shared_data.get("ai_batch", {})
        
        # 只显示 Emotion 类别，因为shared主要用于情绪词汇
        emotions_batch = ai_batch.get("emotion", [])
        st.markdown("#### 💭 Emotion (情绪词汇) - 支持权重")
        
        col1, col2 = st.columns(2)
        
        # 分两列显示情绪词汇
        for i, item in enumerate(emotions_batch):
            word = item.get("word", "")
            weight = item.get("weight", 2)
            
            # 交替显示在两列中
            target_col = col1 if i % 2 == 0 else col2
            
            with target_col:
                col_word, col_weight, col_del = st.columns([3,2,1])
                with col_word:
                    new_word = st.text_input(f"情绪词汇", value=word, key=f"shared_emotion_word_{i}")
                    if new_word != word:
                        emotions_batch[i]["word"] = new_word
                with col_weight:
                    new_weight = st.slider("权重", 1, 3, value=weight, key=f"shared_emotion_weight_{i}")
                    if new_weight != weight:
                        emotions_batch[i]["weight"] = new_weight
                with col_del:
                    if st.button("删除", key=f"shared_emotion_delete_{i}"):
                        emotions_batch.pop(i)
                        st.rerun()
        
        # 添加新情绪词汇按钮
        if st.button("➕ 添加新情绪词汇", key="shared_emotion_add"):
            emotions_batch.append({"word": "", "weight": 2})
            st.rerun()
        
        # 更新配置
        if "shared" not in vocab_config:
            vocab_config["shared"] = {}
        if "ai_batch" not in vocab_config["shared"]:
            vocab_config["shared"]["ai_batch"] = {}
        vocab_config["shared"]["ai_batch"]["emotion"] = emotions_batch
        
        # 为了保持其他AI类别的空列表
        for category in ["object", "scene", "brand"]:
            if category not in vocab_config["shared"]["ai_batch"]:
                vocab_config["shared"]["ai_batch"][category] = []
        
        # 显示统计
        valid_emotions = [item for item in emotions_batch if item.get("word", "").strip()]
        if valid_emotions:
            st.success(f"✅ 已配置 {len(valid_emotions)} 个情绪词汇，将用于所有AI模型")
        else:
            st.warning("⚠️ 建议至少配置10-20个情绪词汇以获得最佳AI识别效果")

    st.markdown("---")

    module_mapping = {
        "pain_points": "模块一：痛点 (Pain Points)",
        "solutions": "模块二：解决方案导入 (Solutions)",
        "features_formula": "模块三：卖点·成分&配方 (Features & Formula)",
        "promotions": "模块四：促销机制 (Promotions)"
    }
    for key, title in module_mapping.items():
        with st.expander(title, expanded=False):
            module_data = vocab_config.get(key, {})
            st.markdown("### 🆕 批量定义 (AI Batch) - 精确控制AI类别")
            ai_batch = module_data.get("ai_batch", {})
            col1, col2 = st.columns(2)
            with col1:
                # Object
                objects_batch = ai_batch.get("object", [])
                st.markdown("#### 🎯 Object (物体/行为) - 支持权重")
                for i, item in enumerate(objects_batch):
                    word = item.get("word", "")
                    weight = item.get("weight", 2)
                    col_word, col_weight, col_del = st.columns([3,2,1])
                    with col_word:
                        new_word = st.text_input(f"词汇{i}", value=word, key=f"{key}_object_word_{i}")
                        if new_word != word:
                            objects_batch[i]["word"] = new_word
                    with col_weight:
                        new_weight = st.slider("权重", 1, 3, value=weight, key=f"{key}_object_weight_{i}")
                        if new_weight != weight:
                            objects_batch[i]["weight"] = new_weight
                    with col_del:
                        if st.button("删除", key=f"{key}_object_delete_{i}"):
                            objects_batch.pop(i)
                            st.rerun()
                if st.button("添加新词", key=f"{key}_object_add"):
                    objects_batch.append({"word": "", "weight": 2})
                    st.rerun()
                if "ai_batch" not in vocab_config[key]: vocab_config[key]["ai_batch"] = {}
                vocab_config[key]["ai_batch"]["object"] = objects_batch
            with col2:
                # Emotion
                emotions_batch = ai_batch.get("emotion", [])
                st.markdown("#### 💭 Emotion (情绪/价值) - 支持权重")
                for i, item in enumerate(emotions_batch):
                    word = item.get("word", "")
                    weight = item.get("weight", 2)
                    col_word, col_weight, col_del = st.columns([3,2,1])
                    with col_word:
                        new_word = st.text_input(f"情绪词汇{i}", value=word, key=f"{key}_emotion_word_{i}")
                        if new_word != word:
                            emotions_batch[i]["word"] = new_word
                    with col_weight:
                        new_weight = st.slider("权重", 1, 3, value=weight, key=f"{key}_emotion_weight_{i}")
                        if new_weight != weight:
                            emotions_batch[i]["weight"] = new_weight
                    with col_del:
                        if st.button("删除", key=f"{key}_emotion_delete_{i}"):
                            emotions_batch.pop(i)
                            st.rerun()
                if st.button("添加新情绪", key=f"{key}_emotion_add"):
                    emotions_batch.append({"word": "", "weight": 2})
                    st.rerun()
                if "ai_batch" not in vocab_config[key]: vocab_config[key]["ai_batch"] = {}
                vocab_config[key]["ai_batch"]["emotion"] = emotions_batch
            with col1:
                # Scene
                scenes_batch = ai_batch.get("scene", [])
                st.markdown("#### 🏞️ Scene (场景/环境) - 支持权重")
                for i, item in enumerate(scenes_batch):
                    word = item.get("word", "")
                    weight = item.get("weight", 2)
                    col_word, col_weight, col_del = st.columns([3,2,1])
                    with col_word:
                        new_word = st.text_input(f"场景词汇{i}", value=word, key=f"{key}_scene_word_{i}")
                        if new_word != word:
                            scenes_batch[i]["word"] = new_word
                    with col_weight:
                        new_weight = st.slider("权重", 1, 3, value=weight, key=f"{key}_scene_weight_{i}")
                        if new_weight != weight:
                            scenes_batch[i]["weight"] = new_weight
                    with col_del:
                        if st.button("删除", key=f"{key}_scene_delete_{i}"):
                            scenes_batch.pop(i)
                            st.rerun()
                if st.button("添加新场景", key=f"{key}_scene_add"):
                    scenes_batch.append({"word": "", "weight": 2})
                    st.rerun()
                if "ai_batch" not in vocab_config[key]: vocab_config[key]["ai_batch"] = {}
                vocab_config[key]["ai_batch"]["scene"] = scenes_batch
            with col2:
                # Brand
                brands_batch = ai_batch.get("brand", [])
                st.markdown("#### 🏷️ Brand (品牌标识) - 支持权重")
                for i, item in enumerate(brands_batch):
                    word = item.get("word", "")
                    weight = item.get("weight", 2)
                    col_word, col_weight, col_del = st.columns([3,2,1])
                    with col_word:
                        new_word = st.text_input(f"品牌词汇{i}", value=word, key=f"{key}_brand_word_{i}")
                        if new_word != word:
                            brands_batch[i]["word"] = new_word
                    with col_weight:
                        new_weight = st.slider("权重", 1, 3, value=weight, key=f"{key}_brand_weight_{i}")
                        if new_weight != weight:
                            brands_batch[i]["weight"] = new_weight
                    with col_del:
                        if st.button("删除", key=f"{key}_brand_delete_{i}"):
                            brands_batch.pop(i)
                            st.rerun()
                if st.button("添加新品牌", key=f"{key}_brand_add"):
                    brands_batch.append({"word": "", "weight": 2})
                    st.rerun()
                if "ai_batch" not in vocab_config[key]: vocab_config[key]["ai_batch"] = {}
                vocab_config[key]["ai_batch"]["brand"] = brands_batch
            
            # 🆕 Negative Keywords 编辑区域
            st.markdown("#### 🚫 Negative Keywords (排除关键词)")
            negative_keywords = module_data.get("negative_keywords", [])
            
            col_neg1, col_neg2 = st.columns([4, 1])
            with col_neg1:
                st.markdown("**排除关键词列表** - 包含这些词的片段将不会被分类到本模块")
                for i, neg_word in enumerate(negative_keywords):
                    col_word, col_del = st.columns([4, 1])
                    with col_word:
                        new_neg_word = st.text_input(f"排除词{i}", value=neg_word, key=f"{key}_negative_{i}")
                        if new_neg_word != neg_word:
                            negative_keywords[i] = new_neg_word
                    with col_del:
                        if st.button("删除", key=f"{key}_negative_delete_{i}"):
                            negative_keywords.pop(i)
                            st.rerun()
            
            with col_neg2:
                if st.button("添加排除词", key=f"{key}_negative_add"):
                    negative_keywords.append("")
                    st.rerun()
            
            vocab_config[key]["negative_keywords"] = negative_keywords
            
            # 🆕 显示排除关键词说明
            if negative_keywords:
                valid_negatives = [neg for neg in negative_keywords if neg.strip()]
                if valid_negatives:
                    st.success(f"✅ 已配置 {len(valid_negatives)} 个排除关键词，将过滤相关片段")
                else:
                    st.warning("⚠️ 排除关键词列表为空，建议添加以提高分类精度")
            
            if ai_batch:
                st.info("ℹ️ **使用批量定义**: 此模块将优先使用上面的批量定义，传统字段将被忽略。")
            st.markdown("---")

    # --- 全局配置编辑 ---
    with st.expander("全局配置 (Global Settings)", expanded=False):
        global_settings = vocab_config.get("global_settings", {})
        st.markdown("**规则微调 (Overrides)**")
        overrides = global_settings.get("overrides", {})
        pain_neg = overrides.get("pain_points_negatives", [])
        pain_neg_text = ", ".join(pain_neg)
        new_pain_neg_text = st.text_area("痛点模块排除词", value=pain_neg_text, key="pain_neg")
        if new_pain_neg_text != pain_neg_text:
            if "overrides" not in vocab_config["global_settings"]: vocab_config["global_settings"]["overrides"] = {}
            vocab_config["global_settings"]["overrides"]["pain_points_negatives"] = [w.strip() for w in new_pain_neg_text.split(",") if w.strip()]
        promo_neg = overrides.get("promotions_negatives", [])
        promo_neg_text = ", ".join(promo_neg)
        new_promo_neg_text = st.text_area("促销机制模块排除词", value=promo_neg_text, key="promo_neg")
        if new_promo_neg_text != promo_neg_text:
            if "overrides" not in vocab_config["global_settings"]: vocab_config["global_settings"]["overrides"] = {}
            vocab_config["global_settings"]["overrides"]["promotions_negatives"] = [w.strip() for w in new_promo_neg_text.split(",") if w.strip()]

    # --- 保存按钮 ---
    save_col = st.empty()
    if save_col.button("💾 保存业务蓝图", type="primary"):
        try:
            with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
                yaml.dump(vocab_config, f, allow_unicode=True, sort_keys=False, indent=2)
            st.session_state['save_success'] = True
        except Exception as e:
            st.error(f"❌ 保存失败: {e}")
    if st.session_state.get('save_success'):
        st.success("✅ 保存成功！", icon="✅")
        time.sleep(2)
        st.session_state['save_success'] = False

    st.markdown("---")
    st.info('💡 **所有编辑操作都只在页面内生效，点击"保存业务蓝图"后才会写入配置文件。**')

    # --- 全局排除关键词编辑 ---
    st.markdown("---")
    with st.expander("🚫 全局排除关键词 (Global Exclusion)", expanded=True):
        st.markdown("##### 在此定义的关键词将从所有模块中排除，用于过滤通用无关场景（如路牌、交通灯等）")
        
        # 从 vocab_config (st.session_state) 中获取或初始化
        global_settings = vocab_config.get("global_settings", {})
        if "global_exclusion_keywords" not in global_settings:
            global_settings["global_exclusion_keywords"] = []
        
        exclusion_keywords = global_settings["global_exclusion_keywords"]

        # 使用循环和 key 来动态创建和管理输入框
        for i in range(len(exclusion_keywords)):
            col_word, col_del = st.columns([4, 1])
            with col_word:
                new_keyword = st.text_input(f"全局排除词 {i+1}", value=exclusion_keywords[i], key=f"global_exclude_{i}")
                if new_keyword != exclusion_keywords[i]:
                    exclusion_keywords[i] = new_keyword
            with col_del:
                if st.button("删除", key=f"global_exclude_del_{i}"):
                    exclusion_keywords.pop(i)
                    st.rerun()

        if st.button("➕ 添加全局排除词", key="global_exclude_add"):
            exclusion_keywords.append("")
            st.rerun()
            
        # 将修改写回 vocab_config
        vocab_config["global_settings"] = global_settings
        
        if exclusion_keywords:
            valid_exclusions = [kw for kw in exclusion_keywords if kw.strip()]
            if valid_exclusions:
                st.success(f"✅ 已配置 {len(valid_exclusions)} 个全局排除关键词。保存后，包含这些词的片段将不会被选用。")

    # --- 预览AI Prompt ---
    st.markdown("---")
    st.subheader("👁️ AI Prompt 预览")
    
    if st.button("🔍 预览当前配置生成的AI Prompt"):
        vocab = config_manager.get_ai_vocabulary()
        st.json({k: list(v) for k, v in vocab.items()})

        # Qwen视觉分析Prompt
        from modules.ai_analyzers.qwen_video_analyzer import QwenVideoAnalyzer
        analyzer = QwenVideoAnalyzer()
        prompt = analyzer._get_fallback_visual_prompt() # 调用重构后的方法
        st.text_area("Qwen视觉分析Prompt预览", prompt, height=600)

        # DeepSeek音频分析Prompt（标签生成兜底）
        from utils.keyword_config import get_deepseek_audio_prompt_for_labeling, get_deepseek_audio_prompt_for_mapping
        deepseek_labeling_prompt = get_deepseek_audio_prompt_for_labeling()
        st.text_area("DeepSeek音频分析Prompt（标签生成兜底）", deepseek_labeling_prompt, height=300)

        # DeepSeek音频分析Prompt（业务归类兜底）
        deepseek_mapping_prompt = get_deepseek_audio_prompt_for_mapping()
        st.text_area("DeepSeek音频分析Prompt（业务归类兜底）", deepseek_mapping_prompt, height=600)

if __name__ == "__main__":
    main() 