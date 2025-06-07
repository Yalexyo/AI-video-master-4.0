"""
组装工厂UI组件模块
提取和封装组装工厂的用户界面组件
"""

import streamlit as st
import os
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path

# 导入配置
from streamlit_app.config.factory_config import FactoryConfig


def render_video_upload_section() -> Optional[Any]:
    """渲染视频上传区域
    
    Returns:
        上传的视频文件对象或None
    """
    st.markdown("### 📤 视频上传")
    
    config = FactoryConfig.get_assembly_config()
    
    col1, col2 = st.columns(2)
    
    with col1:
        uploaded_video = st.file_uploader(
            "选择视频文件",
            type=config["supported_video_formats"],
            help="上传视频文件进行智能分析和切分"
        )
    
    with col2:
        use_sample_video = st.checkbox(
            "使用示例视频",
            help="使用Google Cloud提供的示例视频（cat.mp4）",
            key="assembly_use_sample_video"
        )
    
    return uploaded_video, use_sample_video


def render_analysis_features() -> Dict[str, bool]:
    """渲染分析功能选择
    
    Returns:
        Dict: 包含各功能启用状态的字典
    """
    st.markdown("### 🔧 分析功能选择")
    
    # 基础功能
    col1, col2 = st.columns(2)
    
    with col1:
        shot_detection = st.checkbox(
            "🎬 镜头检测",
            value=True,
            help="检测视频中的镜头切换",
            key="assembly_shot_detection"
        )
        
        label_detection = st.checkbox(
            "🏷️ 标签检测", 
            value=True,
            help="识别视频中的物体和场景",
            key="assembly_label_detection"
        )
    
    with col2:
        object_tracking = st.checkbox(
            "📍 对象跟踪",
            value=False,
            help="跟踪视频中的特定对象",
            key="assembly_object_tracking"
        )
        
        auto_cleanup = st.checkbox(
            "🧹 自动清理",
            value=True,
            help="分析完成后自动清理云端文件",
            key="assembly_auto_cleanup"
        )
    
    return {
        "shot_detection": shot_detection,
        "label_detection": label_detection,
        "object_tracking": object_tracking,
        "auto_cleanup": auto_cleanup
    }


def render_batch_analysis_settings() -> Dict[str, Any]:
    """渲染批量分析设置
    
    Returns:
        Dict: 批量分析设置参数
    """
    st.markdown("### ⚙️ 分析设置")
    
    config = FactoryConfig.get_assembly_config()
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        batch_size = st.number_input(
            "批处理大小",
            min_value=1,
            max_value=10,
            value=config["default_batch_size"],
            help="同时处理的视频片段数量"
        )
    
    with col2:
        min_empty_tags = st.number_input(
            "空标签阈值",
            min_value=1,
            max_value=5,
            value=config["min_empty_tags"],
            help="触发DeepSeek兜底分析的空标签数量"
        )
    
    with col3:
        # 🚀 新增：并行工作线程数配置
        max_workers = st.number_input(
            "并行线程数",
            min_value=1,
            max_value=8,
            value=3,
            help="并行分析的最大线程数，影响分析速度"
        )
    
    with col4:
        auto_merge_results = st.checkbox(
            "自动合并分析结果",
            value=config["auto_merge_results"],
            help="将多个模型的分析结果自动合并",
            key="assembly_auto_merge_results"
        )
    
    return {
        "batch_size": batch_size,
        "min_empty_tags": min_empty_tags,
        "max_workers": max_workers,
        "auto_merge_results": auto_merge_results
    }


def render_clustering_settings() -> Dict[str, float]:
    """渲染聚类设置
    
    Returns:
        Dict: 聚类设置参数
    """
    st.markdown("### 🧠 场景聚类设置")
    
    config = FactoryConfig.get_assembly_config()
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        similarity_threshold = st.slider(
            "相似度阈值",
            min_value=0.5,
            max_value=1.0,
            value=config["default_similarity_threshold"],
            step=0.05,
            help="场景相似度判断阈值，越高越严格"
        )
    
    with col2:
        min_scene_duration = st.number_input(
            "最小场景时长 (秒)",
            min_value=1.0,
            max_value=10.0,
            value=config["default_min_scene_duration"],
            step=0.5,
            help="合并后场景的最小时长要求"
        )
    
    with col3:
        max_scenes = st.number_input(
            "最大场景数",
            min_value=5,
            max_value=50,
            value=config["default_max_scenes"],
            help="聚类后保留的最大场景数量"
        )
    
    return {
        "similarity_threshold": similarity_threshold,
        "min_scene_duration": min_scene_duration,
        "max_scenes": max_scenes
    }


def render_video_selector(context: str = "default") -> Tuple[Optional[str], List[Any]]:
    """渲染视频选择器
    
    Args:
        context: 上下文标识符，用于生成唯一的key
    
    Returns:
        Tuple: (选中的视频ID, 片段文件列表)
    """
    st.markdown("### 📁 视频片段选择")
    
    # 扫描可用的视频目录
    config = FactoryConfig.get_assembly_config()
    video_pool_path = Path(config["default_video_pool_path"])
    
    if not video_pool_path.exists():
        st.warning(f"⚠️ 视频池目录不存在: {video_pool_path}")
        return None, []
    
    # 获取所有视频目录
    video_dirs = [d for d in video_pool_path.iterdir() if d.is_dir()]
    
    if not video_dirs:
        st.info("📂 视频池为空，请先使用零件工厂处理一些视频")
        return None, []
    
    # 视频选择 - 使用唯一的key
    video_ids = [d.name for d in video_dirs]
    selected_video_id = st.selectbox(
        "选择要分析的视频",
        options=video_ids,
        help="选择已切分的视频进行标签分析",
        key=f"assembly_factory_video_selector_{context}"
    )
    
    if selected_video_id:
        video_dir = video_pool_path / selected_video_id
        segment_files = list(video_dir.glob("*.mp4"))
        
        if segment_files:
            st.info(f"📊 找到 {len(segment_files)} 个视频片段")
            
            # 显示前几个文件名作为预览
            preview_files = segment_files[:3]
            preview_names = [f.name for f in preview_files]
            
            if len(segment_files) > 3:
                preview_names.append(f"... 还有 {len(segment_files) - 3} 个文件")
            
            st.code("\n".join(preview_names))
            
            return selected_video_id, segment_files
        else:
            st.warning("⚠️ 该视频目录中没有找到MP4片段文件")
            return selected_video_id, []
    
    return None, []


def render_analysis_results_display(results: Dict[str, Any], analysis_type: str = "default") -> None:
    """渲染分析结果显示
    
    Args:
        results: 分析结果字典
        analysis_type: 分析类型标识符
    """
    if not results:
        st.info("暂无分析结果")
        return
    
    # 结果概览
    if isinstance(results, list):
        st.metric("分析片段数", len(results))
        
        # 创建结果表格
        import pandas as pd
        
        display_data = []
        for result in results:
            display_data.append({
                "文件名": result.get("file_name", "N/A"),
                "大小(MB)": f"{result.get('file_size', 0):.1f}",
                "模型": result.get("model", "Unknown"),
                "物体": result.get("object", "无"),
                "场景": result.get("sence", "无"),
                "情感": result.get("emotion", "无"),
                "置信度": f"{result.get('confidence', 0):.2f}"
            })
        
        if display_data:
            df = pd.DataFrame(display_data)
            st.dataframe(df, use_container_width=True)
        
        # 统计信息
        _render_analysis_statistics(results)
    
    elif isinstance(results, dict):
        # 单个结果显示
        st.json(results)


def _render_analysis_statistics(results: List[Dict[str, Any]]) -> None:
    """渲染分析统计信息
    
    Args:
        results: 分析结果列表
    """
    if not results:
        return
    
    st.markdown("#### 📊 分析统计")
    
    # 基本统计
    total_count = len(results)
    success_count = len([r for r in results if r.get("success", False)])
    avg_confidence = sum(r.get("confidence", 0) for r in results) / total_count if total_count > 0 else 0
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("总片段", total_count)
    with col2:
        st.metric("成功分析", success_count)
    with col3:
        st.metric("成功率", f"{success_count/total_count*100:.1f}%" if total_count > 0 else "0%")
    with col4:
        st.metric("平均置信度", f"{avg_confidence:.2f}")
    
    # 模型使用统计
    model_counts = {}
    for result in results:
        model = result.get("model", "Unknown")
        model_counts[model] = model_counts.get(model, 0) + 1
    
    if model_counts:
        st.markdown("**模型使用分布:**")
        for model, count in model_counts.items():
            percentage = count / total_count * 100
            st.text(f"• {model}: {count} 个片段 ({percentage:.1f}%)")


def render_progress_tracking(phase: str, current: int, total: int, status: str = "") -> None:
    """渲染进度跟踪
    
    Args:
        phase: 当前阶段
        current: 当前进度
        total: 总数
        status: 状态文本
    """
    progress_value = current / total if total > 0 else 0
    
    st.progress(progress_value)
    
    progress_text = f"**{phase}**: {current}/{total}"
    if status:
        progress_text += f" - {status}"
    
    st.text(progress_text)


def render_credentials_check() -> bool:
    """渲染凭据检查
    
    Returns:
        bool: 凭据是否有效
    """
    st.markdown("### 🔐 API凭据检查")
    
    config = FactoryConfig.get_assembly_config()
    
    # Google Cloud凭据检查
    if st.button("🔍 检查Google Cloud凭据", key="assembly_check_credentials"):
        try:
            from streamlit_app.modules.ai_analyzers import GoogleVideoAnalyzer
            analyzer = GoogleVideoAnalyzer()
            has_credentials, cred_path = analyzer.check_credentials()
            
            if has_credentials:
                st.success(f"✅ Google Cloud凭据有效: {cred_path}")
                return True
            else:
                st.error("❌ Google Cloud凭据无效或未设置")
                st.info("请在设置页面配置Google Cloud凭据文件")
                return False
        except Exception as e:
            st.error(f"❌ 检查Google Cloud凭据时出错: {e}")
            return False
    
    # DeepSeek API检查
    if config["deepseek_enabled"]:
        if config["deepseek_api_key"]:
            st.success("✅ DeepSeek API密钥已配置")
        else:
            st.warning("⚠️ DeepSeek API密钥未配置")
            st.info("请设置环境变量 DEEPSEEK_API_KEY")
    
    return True


def render_action_buttons(analysis_type: str = "default") -> Dict[str, bool]:
    """渲染操作按钮
    
    Args:
        analysis_type: 分析类型
        
    Returns:
        Dict: 按钮点击状态
    """
    col1, col2, col3 = st.columns(3)
    
    buttons = {}
    
    with col1:
        buttons["start_analysis"] = st.button(
            "🚀 开始分析",
            type="primary",
            help="开始执行选定的分析任务",
            key=f"assembly_start_analysis_{analysis_type}"
        )
    
    with col2:
        buttons["save_results"] = st.button(
            "💾 保存结果",
            help="将分析结果保存到文件",
            key=f"assembly_save_results_{analysis_type}"
        )
    
    with col3:
        buttons["export_csv"] = st.button(
            "📊 导出CSV",
            help="将结果导出为CSV格式",
            key=f"assembly_export_csv_{analysis_type}"
        )
    
    return buttons


def render_error_display(error: Exception, context: str = "") -> None:
    """渲染错误信息显示
    
    Args:
        error: 异常对象
        context: 错误上下文信息
    """
    if context:
        st.error(f"❌ {context}: {str(error)}")
    else:
        st.error(f"❌ 处理过程中出错: {str(error)}")
    
    # 显示错误详情
    with st.expander("🔍 错误详情", expanded=False):
        import traceback
        st.code(traceback.format_exc(), language="python")


def render_model_selection() -> Dict[str, bool]:
    """渲染模型选择界面
    
    Returns:
        Dict: 模型启用状态
    """
    st.markdown("### 🤖 AI模型选择")
    
    config = FactoryConfig.get_assembly_config()
    
    col1, col2, col3 = st.columns(3)
    
    models = {}
    
    with col1:
        models["google_cloud"] = st.checkbox(
            "🌩️ Google Cloud Video Intelligence",
            value=config["google_cloud_enabled"],
            help="使用Google Cloud进行视频分析",
            key="assembly_model_google_cloud"
        )
    
    with col2:
        models["qwen"] = st.checkbox(
            "🤖 Qwen模型",
            value=config["qwen_enabled"],
            help="使用Qwen进行视觉理解分析",
            key="assembly_model_qwen"
        )
    
    with col3:
        models["deepseek"] = st.checkbox(
            "🧠 DeepSeek模型",
            value=config["deepseek_enabled"],
            help="使用DeepSeek进行智能分析兜底",
            key="assembly_model_deepseek"
        )
    
    return models 


def render_prompt_configuration() -> None:
    """渲染优化的AI模型与业务逻辑配置界面"""
    st.markdown("### 🎯 智能配置中心")
    
    st.info("""
    🔍 **配置逻辑说明**：
    1. **AI识别词库** → 定义AI能"看到"和"听到"什么
    2. **业务分类规则** → 定义识别结果如何映射到业务模块
    3. **Prompt预览** → 查看最终生成的AI指令
    """)
    
    # 创建标签页
    tab1, tab2 = st.tabs([
        "🤖 AI识别词库", 
        "🔍 Prompt预览"
    ])
    
    with tab1:
        _render_ai_recognition_config()
        
    with tab2:
        _render_prompt_previews()
    
    # 💡 提示：业务分类规则配置已移至调试工厂
    st.info("""
    🔧 **业务分类规则配置功能已迁移至调试工厂！**
    
    📍 **新功能位置**: 🐛 调试工厂 → 📋 映射规则详细检查
    
    🎯 **升级优势**:
    - ✅ 实时规则预览和编辑
    - ✅ 立即测试修改效果  
    - ✅ 可视化调试过程
    - ✅ 排除关键词验证
    
    👉 点击左侧导航中的 🐛调试工厂 进行规则配置
    """)


def _render_ai_recognition_config() -> None:
    """渲染AI识别配置界面"""
    import time
    
    st.markdown("#### 🤖 AI识别词库配置")
    st.write("配置AI模型识别视频内容时使用的基础词汇表")
    
    try:
        from streamlit_app.utils.optimized_keyword_manager import keyword_manager
        current_config = keyword_manager.get_ai_recognition_config()
    except ImportError:
        st.error("无法导入优化的关键词管理器，请检查安装")
        return
    
    # 视觉AI配置
    with st.expander("👁️ **视觉AI (Qwen) 识别词库**", expanded=True):
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📦 识别对象")
            
            # 基础对象
            basic_objects_str = ", ".join(current_config["visual"]["objects_basic"])
            new_basic_objects_str = st.text_area(
                "基础对象",
                value=basic_objects_str,
                placeholder="奶粉罐, 奶瓶, 宝宝, 妈妈",
                help="AI识别的基础视觉对象",
                key="qwen_basic_objects",
                height=80
            )
            
            # 品牌相关对象
            brand_objects_str = ", ".join(current_config["visual"]["objects_brand"])
            new_brand_objects_str = st.text_area(
                "品牌相关对象",
                value=brand_objects_str,
                placeholder="品牌logo, 包装, 商标",
                help="与品牌识别相关的视觉元素",
                key="qwen_brand_objects",
                height=80
            )
            
            # 成分相关对象
            comp_objects_str = ", ".join(current_config["visual"]["objects_composition"])
            new_comp_objects_str = st.text_area(
                "成分相关对象",
                value=comp_objects_str,
                placeholder="成分表, 营养表, 配料表",
                help="营养成分和配料表相关对象",
                key="qwen_comp_objects",
                height=80
            )
        
        with col2:
            st.subheader("🏞️ 场景配置")
            
            # 场景
            scenes_str = ", ".join(current_config["visual"]["scenes"])
            new_scenes_str = st.text_area(
                "识别场景",
                value=scenes_str,
                placeholder="厨房, 客厅, 医院, 户外",
                help="AI识别的场景环境",
                key="qwen_scenes",
                height=80
            )
            
        # 品牌配置区域
        st.subheader("🏷️ 品牌识别配置")
        st.info("💡 专注核心品牌：惠氏、启赋、蕴淳，避免配置过多品牌分散AI注意力")
        
        # 🎯 简化品牌配置 - 只显示一个品牌列表
        brands_str = ", ".join(current_config["visual"]["brands"])
        new_brands_str = st.text_area(
            "🎯 核心品牌（建议3-5个）",
            value=brands_str,
            placeholder="惠氏, 启赋, 蕴淳",
            help="AI会重点识别这些品牌，建议专注核心品牌",
            key="qwen_brands",
            height=80
        )
        
        # 保存视觉配置按钮
        if st.button("💾 保存视觉AI配置", type="primary", key="save_visual_config"):
            new_config = {
                "visual": {
                    "objects_basic": [kw.strip() for kw in new_basic_objects_str.split(",") if kw.strip()],
                    "objects_brand": [kw.strip() for kw in new_brand_objects_str.split(",") if kw.strip()],
                    "objects_composition": [kw.strip() for kw in new_comp_objects_str.split(",") if kw.strip()],
                    "scenes": [kw.strip() for kw in new_scenes_str.split(",") if kw.strip()],
                    "brands": [kw.strip() for kw in new_brands_str.split(",") if kw.strip()],
                    "pain_signals": [kw.strip() for kw in new_pain_signals_str.split(",") if kw.strip()],
                    "vitality_signals": [kw.strip() for kw in new_vitality_signals_str.split(",") if kw.strip()]
                },
                "audio": current_config["audio"],
                "shared": current_config["shared"]
            }
            
            # 验证配置
            issues = keyword_manager.validate_config("ai_recognition", new_config)
            if issues:
                st.error("配置验证失败：")
                for issue in issues:
                    st.text(f"• {issue}")
            else:
                success = keyword_manager.save_ai_recognition_config(new_config)
                if success:
                    # 设置成功消息和时间戳
                    import time
                    st.session_state["save_message_visual"] = {
                        "type": "success",
                        "message": "✅ 视觉AI配置保存成功！",
                        "timestamp": time.time()
                    }
                    # 清除缓存并重新加载配置
                    try:
                        from streamlit_app.utils.keyword_config import reload_config
                        reload_config()
                    except ImportError:
                        pass
                    st.rerun()
                else:
                    import time
                    st.session_state["save_message_visual"] = {
                        "type": "error",
                        "message": "❌ 保存失败，请检查文件权限",
                        "timestamp": time.time()
                    }
    
    # 音频AI配置
    with st.expander("🎤 **音频AI (DeepSeek) 识别词库**", expanded=False):
        col1, col2 = st.columns(2)
        
        with col1:
            audio_objects_str = ", ".join(current_config["audio"]["objects"])
            new_audio_objects_str = st.text_area(
                "音频识别对象",
                value=audio_objects_str,
                placeholder="奶粉, 宝宝, 妈妈",
                help="AI从音频中识别的对象",
                key="deepseek_objects",
                height=80
            )
        
        with col2:
            audio_scenes_str = ", ".join(current_config["audio"]["scenes"])
            new_audio_scenes_str = st.text_area(
                "音频识别场景",
                value=audio_scenes_str,
                placeholder="冲奶, 指导, 护理",
                help="AI从音频中识别的场景",
                key="deepseek_scenes",
                height=80
            )
        
        # 保存音频配置按钮
        if st.button("💾 保存音频AI配置", type="primary", key="save_audio_config"):
            new_config = current_config.copy()
            new_config["audio"] = {
                "objects": [kw.strip() for kw in new_audio_objects_str.split(",") if kw.strip()],
                "scenes": [kw.strip() for kw in new_audio_scenes_str.split(",") if kw.strip()]
            }
            
            success = keyword_manager.save_ai_recognition_config(new_config)
            if success:
                # 设置成功消息和时间戳
                import time
                st.session_state["save_message_audio"] = {
                    "type": "success",
                    "message": "✅ 音频AI配置保存成功！",
                    "timestamp": time.time()
                }
                try:
                    from streamlit_app.utils.keyword_config import reload_config
                    reload_config()
                except ImportError:
                    pass
                st.rerun()
            else:
                import time
                st.session_state["save_message_audio"] = {
                    "type": "error",
                    "message": "❌ 保存失败",
                    "timestamp": time.time()
                }
    
    # 通用配置
    with st.expander("🌐 **通用AI配置**", expanded=False):
        emotions_str = " / ".join(current_config["shared"]["emotions"])
        new_emotions_str = st.text_input(
            "可识别情绪（必须5个，用 / 分隔）",
            value=emotions_str,
            help="AI模型只能从这5种情绪中选择",
            key="shared_emotions"
        )
        
        # 保存通用配置按钮
        if st.button("💾 保存通用配置", type="primary", key="save_shared_config"):
            emotions = [emo.strip() for emo in new_emotions_str.split("/") if emo.strip()]
            
            if len(emotions) != 5:
                st.error(f"情绪必须是5个，当前为{len(emotions)}个")
            else:
                new_config = current_config.copy()
                new_config["shared"]["emotions"] = emotions
                
                success = keyword_manager.save_ai_recognition_config(new_config)
                if success:
                    # 设置成功消息和时间戳
                    import time
                    st.session_state["save_message_shared"] = {
                        "type": "success",
                        "message": "✅ 通用配置保存成功！",
                        "timestamp": time.time()
                    }
                    try:
                        from streamlit_app.utils.keyword_config import reload_config
                        reload_config()
                    except ImportError:
                        pass
                    st.rerun()
                else:
                    import time
                    st.session_state["save_message_shared"] = {
                        "type": "error",
                        "message": "❌ 保存失败",
                        "timestamp": time.time()
                    }

    # 显示所有AI识别配置的临时消息（如果存在且未过期）
    import time
    for message_key in ["save_message_visual", "save_message_audio", "save_message_shared"]:
        if message_key in st.session_state:
            message_data = st.session_state[message_key]
            elapsed_time = time.time() - message_data["timestamp"]
            
            # 检查消息是否超过3秒
            if elapsed_time < 3:
                if message_data["type"] == "success":
                    st.success(message_data["message"])
                else:
                    st.error(message_data["message"])
            else:
                # 消息过期，删除
                del st.session_state[message_key]




def _render_prompt_previews() -> None:
    """渲染AI模型Prompt预览界面"""
    st.markdown("#### 📝 AI模型Prompt预览")
    st.write("根据当前配置生成的AI模型指令预览（只读）")
    
    try:
        from streamlit_app.utils.keyword_config import sync_prompt_templates
        templates = sync_prompt_templates()
        
        if templates:
            with st.expander("👁️ Qwen视觉分析Prompt", expanded=True):
                if "qwen_visual" in templates:
                    st.code(templates["qwen_visual"], language="text")
                    st.caption(f"Prompt长度: {len(templates['qwen_visual'])} 字符")
                else:
                    st.error("Qwen Prompt生成失败")
            
            with st.expander("🧠 DeepSeek音频分析Prompt", expanded=False):
                if "deepseek_audio" in templates:
                    st.code(templates["deepseek_audio"], language="text")
                    st.caption(f"Prompt长度: {len(templates['deepseek_audio'])} 字符")
                else:
                    st.error("DeepSeek Prompt生成失败")
                    
            if "qwen_retry" in templates:
                with st.expander("🔄 Qwen重试Prompt", expanded=False):
                    st.code(templates["qwen_retry"], language="text")
                    
            # 添加配置效果预览
            st.subheader("🔧 配置效果分析")
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**品牌识别强化效果**")
                qwen_prompt = templates.get("qwen_visual", "")
                brand_mentions = qwen_prompt.count("重点品牌") + qwen_prompt.count("品牌相关") + qwen_prompt.count("成分相关")
                st.metric("品牌强化次数", brand_mentions)
                
                if brand_mentions >= 3:
                    st.success("✅ 品牌识别强化充分")
                else:
                    st.warning("⚠️ 建议增强品牌识别配置")
            
            with col2:
                st.markdown("**Prompt复杂度**")
                total_keywords = len(templates.get("qwen_visual", "").split("、"))
                st.metric("总关键词估算", total_keywords)
                
                if total_keywords > 50:
                    st.success("✅ 关键词配置丰富")
                else:
                    st.info("💡 可考虑添加更多关键词")
        else:
            st.error("无法生成Prompt模板，请检查配置")
            
    except Exception as e:
        st.error(f"Prompt预览失败: {e}")
        st.info("请确保配置正确并已保存") 