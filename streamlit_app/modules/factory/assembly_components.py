"""
组装工厂UI组件模块
提取和封装组装工厂的用户界面组件
"""

import streamlit as st
import os
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path

# 导入配置
from config.factory_config import FactoryConfig


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
                "场景": result.get("scene", "无"),
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
            from modules.ai_analyzers import GoogleVideoAnalyzer
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


def _render_ai_recognition_config() -> None:
    """渲染AI识别配置界面 - 通用配置置顶设计"""
    import time
    
    st.markdown("#### 🤖 AI识别词库配置")
    st.write("配置AI模型识别视频内容时使用的基础词汇表")
    
    st.info("""
    📝 **编辑说明**: 每个字段都可以独立编辑和保存，修改后点击对应的保存按钮即可生效
    """)
    
    try:
        from utils.optimized_keyword_manager import keyword_manager
        current_config = keyword_manager.get_ai_recognition_config()
    except ImportError:
        st.error("无法导入优化的关键词管理器，请检查安装")
        return

    # =============================================================================
    # 🌐 通用AI配置 (置顶显示)
    # =============================================================================
    st.markdown("---")
    st.markdown("### 🌐 通用AI配置")
    st.info("**视觉和音频AI共享的配置**，修改后同时影响两个AI模型的识别能力")
    
    # 🎯 核心品牌配置
    st.write("**🎯 核心品牌配置 (视觉+音频AI共用):**")
    current_brands = current_config.get("shared", {}).get("brands", [])
    brands_str = ", ".join(current_brands)
    
    # 显示当前已保存的标签
    if current_brands:
        st.markdown("**📋 当前已保存的核心品牌:**")
        # 将标签按行显示，每行最多5个
        brand_chunks = [current_brands[i:i+5] for i in range(0, len(current_brands), 5)]
        for chunk in brand_chunks:
            cols = st.columns(len(chunk))
            for i, brand in enumerate(chunk):
                with cols[i]:
                    st.code(brand, language=None)
    else:
        st.info("💡 尚未配置核心品牌，请在下方输入框中添加")
    
    new_brands_str = st.text_area(
        "🎯 核心品牌理念 (权重 2.0):",
        value=brands_str,
        placeholder="illuma, 启赋, 惠氏, 蕴淳, A2",
        help="视觉AI识别logo标识，音频AI识别品牌名称提及",
        key="shared_brands",
        height=80
    )
    
    # 保存品牌按钮
    if st.button("💾 保存核心品牌", key="save_brands", type="primary"):
        new_brands_list = [kw.strip() for kw in new_brands_str.split(",") if kw.strip()]
        try:
            updated_config = current_config.copy()
            if "shared" not in updated_config:
                updated_config["shared"] = {}
            updated_config["shared"]["brands"] = new_brands_list
            keyword_manager.save_ai_recognition_config(updated_config)
            st.success("✅ 核心品牌已保存! (应用于视觉+音频AI)")
            st.info("🔄 标签已更新，请查看上方显示的当前标签")
            st.rerun()
        except Exception as e:
            st.error(f"保存失败: {e}")

    # 🎭 情绪词库配置 (分正面负面)
    st.write("**🎭 情绪词库配置 (视觉+音频AI共用):**")
    
    # 修改为从ai_batch.emotion获取
    shared_config = current_config.get("shared", {})
    ai_batch = shared_config.get("ai_batch", {})
    emotion_items = ai_batch.get("emotion", [])
    
    # 提取word字段
    current_emotions = []
    for item in emotion_items:
        if isinstance(item, dict):
            word = item.get("word", "")
            if word:
                current_emotions.append(word)
        else:
            current_emotions.append(str(item))
    
    # 如果没有ai_batch格式，尝试传统emotions字段作为兜底
    if not current_emotions:
        current_emotions = shared_config.get("emotions", [])
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**😊 正面情绪:**")
        
        # 显示当前已保存的正面情绪标签
        if current_emotions:
            st.markdown("**📋 当前正面情绪标签:**")
            emotion_chunks = [current_emotions[i:i+3] for i in range(0, len(current_emotions), 3)]
            for chunk in emotion_chunks:
                emotion_cols = st.columns(len(chunk))
                for i, emotion in enumerate(chunk):
                    with emotion_cols[i]:
                        st.code(emotion, language=None)
        else:
            st.info("💡 尚未配置正面情绪，请在下方输入")
        
        positive_str = ", ".join(current_emotions)
        new_positive_str = st.text_area(
            "🧠 情绪与痛点 (权重 1.0):",
            value=positive_str,
            height=120,
            help="积极、正向的情绪词汇，如：快乐、开心、活力满满",
            key="positive_emotions"
        )
    
    with col2:
        st.write("**😟 负面情绪:**")
        
        # 显示当前已保存的负面情绪标签
        if current_emotions:
            st.markdown("**📋 当前负面情绪标签:**")
            neg_emotion_chunks = [emotion for emotion in current_emotions if emotion not in positive_emotions]
            neg_emotion_chunks = neg_emotion_chunks[:3]
            for chunk in neg_emotion_chunks:
                neg_emotion_cols = st.columns(1)
                with neg_emotion_cols[0]:
                    st.code(chunk, language=None)
        else:
            st.info("💡 尚未配置负面情绪，请在下方输入")
        
        negative_str = ", ".join(neg_emotion_chunks)
        new_negative_str = st.text_area(
            "🔍 场景与痛点 (权重 1.0):",
            value=negative_str,
            height=120,
            help="消极、负向的情绪词汇，如：焦虑、痛苦、哭闹",
            key="negative_emotions"
        )
    
    # 保存情绪词库按钮
    if st.button("💾 保存情绪词库", key="save_shared_emotions", type="primary"):
        positive_list = [emo.strip() for emo in new_positive_str.split(",") if emo.strip()]
        negative_list = [emo.strip() for emo in new_negative_str.split(",") if emo.strip()]
        combined_emotions = positive_list + negative_list
        
        if len(combined_emotions) < 10:
            st.warning(f"情绪词库较少，建议至少10个，当前为{len(combined_emotions)}个")
        
        try:
            updated_config = current_config.copy()
            if "shared" not in updated_config:
                updated_config["shared"] = {}
            if "ai_batch" not in updated_config["shared"]:
                updated_config["shared"]["ai_batch"] = {}
            
            # 保存为ai_batch格式
            emotion_batch = [{"word": word, "weight": 2} for word in combined_emotions]
            updated_config["shared"]["ai_batch"]["emotion"] = emotion_batch
            
            # 为了兼容性，也保留traditional格式
            updated_config["shared"]["emotions"] = combined_emotions
            
            keyword_manager.save_ai_recognition_config(updated_config)
            st.success(f"✅ 情绪词库已保存! 共{len(combined_emotions)}个情绪词汇 (正面:{len(positive_list)}, 负面:{len(negative_list)})")
            st.info("🔄 标签已更新，请查看上方显示的当前标签")
            st.rerun()
        except Exception as e:
            st.error(f"保存失败: {e}")

    # 通用配置统计
    st.markdown("**📊 通用配置统计:**")
    col_stat1, col_stat2, col_stat3 = st.columns(3)
    with col_stat1:
        brands_count = len(current_config.get("shared", {}).get("brands", []))
        st.metric("核心品牌", brands_count)
    with col_stat2:
        # 优先从ai_batch获取，兜底用传统emotions
        shared_config = current_config.get("shared", {})
        ai_batch = shared_config.get("ai_batch", {})
        emotion_items = ai_batch.get("emotion", [])
        emotions_count = len(emotion_items) if emotion_items else len(shared_config.get("emotions", []))
        st.metric("情绪词汇", emotions_count)
    with col_stat3:
        positive_count = len(positive_emotions)
        negative_count = len(negative_emotions)
        st.metric("正面/负面", f"{positive_count}/{negative_count}")

    # =============================================================================
    # 🔍 视觉AI配置
    # =============================================================================
    
    # 主配置区域 - 采用左右分栏设计
    st.markdown("### 👁️ 视觉AI (Qwen) 识别词库")
    
    # 左右分栏
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("✅ 正面规则")
        
        # 基础对象配置
        st.write("**📦 基础识别对象 (权重 2.0):**")
        
        # 显示当前已保存的基础对象标签
        current_basic_objects = current_config["visual"]["objects_basic"]
        if current_basic_objects:
            st.markdown("**📋 当前基础识别对象:**")
            basic_chunks = [current_basic_objects[i:i+3] for i in range(0, len(current_basic_objects), 3)]
            for chunk in basic_chunks:
                basic_cols = st.columns(len(chunk))
                for i, obj in enumerate(chunk):
                    with basic_cols[i]:
                        st.code(obj, language=None)
        else:
            st.info("💡 尚未配置基础识别对象，请在下方输入")
        
        basic_objects_str = ", ".join(current_basic_objects)
        new_basic_objects_str = st.text_area(
            "基础识别词库 (用逗号分隔)",
            value=basic_objects_str,
            key="qwen_basic_objects",
            height=80,
            help="AI识别的基础视觉对象，如：奶粉罐, 奶瓶, 宝宝, 妈妈"
        )
        
        # 保存基础对象按钮
        if st.button("💾 保存基础对象", key="save_basic_objects"):
            new_basic_list = [kw.strip() for kw in new_basic_objects_str.split(",") if kw.strip()]
            try:
                updated_config = current_config.copy()
                updated_config["visual"]["objects_basic"] = new_basic_list
                keyword_manager.save_ai_recognition_config(updated_config)
                st.success("✅ 基础对象已保存!")
                st.info("🔄 标签已更新，请查看上方显示的当前标签")
                st.rerun()
            except Exception as e:
                st.error(f"保存失败: {e}")
        
        # 品牌相关对象配置
        st.write("**🏷️ 品牌识别对象 (权重 1.5):**")
        brand_objects_str = ", ".join(current_config["visual"]["objects_brand"])
        new_brand_objects_str = st.text_area(
            "编辑品牌识别对象",
            value=brand_objects_str,
            key="qwen_brand_objects",
            height=80,
            help="与品牌识别相关的视觉元素，如：品牌logo, 包装, 商标"
        )
        
        # 保存品牌对象按钮
        if st.button("💾 保存品牌对象", key="save_brand_objects"):
            new_brand_list = [kw.strip() for kw in new_brand_objects_str.split(",") if kw.strip()]
            try:
                updated_config = current_config.copy()
                updated_config["visual"]["objects_brand"] = new_brand_list
                keyword_manager.save_ai_recognition_config(updated_config)
                st.success("✅ 品牌对象已保存!")
                st.rerun()
            except Exception as e:
                st.error(f"保存失败: {e}")
        
        # 成分相关对象配置
        st.write("**🧪 成分识别对象 (权重 1.5):**")
        comp_objects_str = ", ".join(current_config["visual"]["objects_composition"])
        new_comp_objects_str = st.text_area(
            "编辑成分识别对象",
            value=comp_objects_str,
            key="qwen_comp_objects",
            height=80,
            help="营养成分和配料表相关对象，如：成分表, 营养表, 配料表"
        )
        
        # 保存成分对象按钮
        if st.button("💾 保存成分对象", key="save_comp_objects"):
            new_comp_list = [kw.strip() for kw in new_comp_objects_str.split(",") if kw.strip()]
            try:
                updated_config = current_config.copy()
                updated_config["visual"]["objects_composition"] = new_comp_list
                keyword_manager.save_ai_recognition_config(updated_config)
                st.success("✅ 成分对象已保存!")
                st.rerun()
            except Exception as e:
                st.error(f"保存失败: {e}")
        
        # 医疗对象配置
        st.write("**🏥 医疗相关对象 (权重 1.0):**")
        medical_objects_str = ", ".join(current_config["visual"].get("objects_medical", []))
        new_medical_objects_str = st.text_area(
            "编辑医疗相关对象",
            value=medical_objects_str,
            key="qwen_medical_objects",
            height=80,
            help="医疗场景相关对象，如：输液管, 病床, 医疗设备, 药品"
        )
        
        # 保存医疗对象按钮
        if st.button("💾 保存医疗对象", key="save_medical_objects"):
            new_medical_list = [kw.strip() for kw in new_medical_objects_str.split(",") if kw.strip()]
            try:
                updated_config = current_config.copy()
                updated_config["visual"]["objects_medical"] = new_medical_list
                keyword_manager.save_ai_recognition_config(updated_config)
                st.success("✅ 医疗对象已保存!")
                st.rerun()
            except Exception as e:
                st.error(f"保存失败: {e}")
    
    with col2:
        st.subheader("🏞️ 场景与信号")
        
        # 场景配置
        st.write("**🏞️ 识别场景 (权重 1.0):**")
        scenes_str = ", ".join(current_config["visual"]["scenes"])
        new_scenes_str = st.text_area(
            "编辑识别场景",
            value=scenes_str,
            key="qwen_scenes",
            height=80,
            help="AI识别的场景环境，如：厨房, 客厅, 医院, 户外"
        )
        
        # 保存场景按钮
        if st.button("💾 保存识别场景", key="save_scenes"):
            new_scenes_list = [kw.strip() for kw in new_scenes_str.split(",") if kw.strip()]
            try:
                updated_config = current_config.copy()
                updated_config["visual"]["scenes"] = new_scenes_list
                keyword_manager.save_ai_recognition_config(updated_config)
                st.success("✅ 识别场景已保存!")
                st.rerun()
            except Exception as e:
                st.error(f"保存失败: {e}")
        
        # 情感配置提示 - 使用共用情绪
        st.write("**🎭 情感识别配置:**")
        st.info("💡 视觉AI使用上方共用情绪配置，无需单独设置")
        
        # 场景细分配置
        st.markdown("---")
        st.write("**🏠 场景细分配置:**")
        
        # 室内场景
        indoor_scenes_str = ", ".join(current_config["visual"].get("scenes_indoor", []))
        new_indoor_scenes_str = st.text_area(
            "🏠 室内场景",
            value=indoor_scenes_str,
            key="qwen_indoor_scenes",
            height=70,
            help="室内环境场景，如：厨房, 客厅, 卧室, 婴儿房"
        )
        
        # 户外场景
        outdoor_scenes_str = ", ".join(current_config["visual"].get("scenes_outdoor", []))
        new_outdoor_scenes_str = st.text_area(
            "🌳 户外场景",
            value=outdoor_scenes_str,
            key="qwen_outdoor_scenes",
            height=70,
            help="户外环境场景，如：公园, 游乐场, 滑梯, 蹦床"
        )
        
        # 医疗场景
        medical_scenes_str = ", ".join(current_config["visual"].get("scenes_medical", []))
        new_medical_scenes_str = st.text_area(
            "🏥 医疗场景",
            value=medical_scenes_str,
            key="qwen_medical_scenes",
            height=70,
            help="医疗环境场景，如：医院, 病房, 诊所"
        )
        
        # 演示场景
        demo_scenes_str = ", ".join(current_config["visual"].get("scenes_demonstration", []))
        new_demo_scenes_str = st.text_area(
            "📹 演示场景",
            value=demo_scenes_str,
            key="qwen_demo_scenes",
            height=70,
            help="产品演示场景，如：台面操作, 产品演示, 冲奶演示"
        )
        
        # 保存场景细分按钮
        if st.button("💾 保存场景细分", key="save_scene_details"):
            try:
                updated_config = current_config.copy()
                updated_config["visual"]["scenes_indoor"] = [s.strip() for s in new_indoor_scenes_str.split(",") if s.strip()]
                updated_config["visual"]["scenes_outdoor"] = [s.strip() for s in new_outdoor_scenes_str.split(",") if s.strip()]
                updated_config["visual"]["scenes_medical"] = [s.strip() for s in new_medical_scenes_str.split(",") if s.strip()]
                updated_config["visual"]["scenes_demonstration"] = [s.strip() for s in new_demo_scenes_str.split(",") if s.strip()]
                keyword_manager.save_ai_recognition_config(updated_config)
                st.success("✅ 场景细分已保存!")
                st.rerun()
            except Exception as e:
                st.error(f"保存失败: {e}")
    


    # 视觉配置统计
    st.markdown("---")
    st.subheader("📊 视觉AI配置统计")
    
    col_stat1, col_stat2, col_stat3, col_stat4, col_stat5, col_stat6 = st.columns(6)
    
    with col_stat1:
        basic_count = len(current_config["visual"]["objects_basic"])
        st.metric("基础识别对象", basic_count)
    
    with col_stat2:
        brand_obj_count = len(current_config["visual"]["objects_brand"])
        st.metric("品牌识别对象", brand_obj_count)
    
    with col_stat3:
        comp_obj_count = len(current_config["visual"]["objects_composition"])
        st.metric("成分识别对象", comp_obj_count)
    
    with col_stat4:
        medical_obj_count = len(current_config["visual"].get("objects_medical", []))
        st.metric("医疗相关对象", medical_obj_count)
    
    with col_stat5:
        scenes_count = len(current_config["visual"]["scenes"])
        st.metric("识别场景", scenes_count)
    
    with col_stat6:
        brands_count = len(current_config["visual"]["brands"])
        st.metric("核心品牌", brands_count)
    

    
    # 音频AI配置
    st.markdown("---")
    st.markdown("### 🎤 音频AI (DeepSeek) 识别词库")
    
    # 左右分栏 - 与视觉AI保持一致的结构
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("✅ 正面规则")
        
        # 音频对象配置
        st.write("**📦 基础识别对象 (权重 2.0):**")
        audio_objects_str = ", ".join(current_config["audio"]["objects"])
        new_audio_objects_str = st.text_area(
            "编辑基础识别对象",
            value=audio_objects_str,
            key="deepseek_objects",
            height=80,
            help="AI从音频中识别的对象，如：奶粉, 宝宝, 妈妈"
        )
        
        # 保存音频对象按钮
        if st.button("💾 保存基础对象", key="save_audio_objects"):
            new_audio_objects_list = [kw.strip() for kw in new_audio_objects_str.split(",") if kw.strip()]
            try:
                updated_config = current_config.copy()
                updated_config["audio"]["objects"] = new_audio_objects_list
                keyword_manager.save_ai_recognition_config(updated_config)
                st.success("✅ 基础对象已保存!")
                st.rerun()
            except Exception as e:
                st.error(f"保存失败: {e}")
        
        # 品牌提及配置
        st.write("**🏷️ 品牌识别对象 (权重 1.5):**")
        brand_mentions_str = ", ".join(current_config["audio"].get("brand_mentions", []))
        new_brand_mentions_str = st.text_area(
            "编辑品牌识别对象",
            value=brand_mentions_str,
            key="deepseek_brand_mentions",
            height=80,
            help="音频中提及的品牌名称，如：启赋, 惠氏, 蕴淳"
        )
        
        # 保存品牌提及按钮
        if st.button("💾 保存品牌对象", key="save_brand_mentions"):
            new_brand_mentions_list = [kw.strip() for kw in new_brand_mentions_str.split(",") if kw.strip()]
            try:
                updated_config = current_config.copy()
                if "brand_mentions" not in updated_config["audio"]:
                    updated_config["audio"]["brand_mentions"] = []
                updated_config["audio"]["brand_mentions"] = new_brand_mentions_list
                keyword_manager.save_ai_recognition_config(updated_config)
                st.success("✅ 品牌对象已保存!")
                st.rerun()
            except Exception as e:
                st.error(f"保存失败: {e}")
        
        # 产品特性配置
        st.write("**🧪 成分识别对象 (权重 1.5):**")
        product_features_str = ", ".join(current_config["audio"].get("product_features", []))
        new_product_features_str = st.text_area(
            "编辑成分识别对象",
            value=product_features_str,
            key="deepseek_product_features",
            height=80,
            help="产品特性和成分描述，如：A2蛋白, DHA, 营养成分"
        )
        
        # 保存产品特性按钮
        if st.button("💾 保存成分对象", key="save_product_features"):
            new_product_features_list = [kw.strip() for kw in new_product_features_str.split(",") if kw.strip()]
            try:
                updated_config = current_config.copy()
                if "product_features" not in updated_config["audio"]:
                    updated_config["audio"]["product_features"] = []
                updated_config["audio"]["product_features"] = new_product_features_list
                keyword_manager.save_ai_recognition_config(updated_config)
                st.success("✅ 成分对象已保存!")
                st.rerun()
            except Exception as e:
                st.error(f"保存失败: {e}")
    
    with col2:
        st.subheader("🏞️ 场景与信号")
        
        # 音频场景配置
        st.write("**🎤 音频识别场景 (权重 1.0):**")
        audio_scenes_str = ", ".join(current_config["audio"]["scenes"])
        new_audio_scenes_str = st.text_area(
            "编辑音频识别场景",
            value=audio_scenes_str,
            key="deepseek_scenes",
            height=80,
            help="AI从音频中识别的场景，如：冲奶演示, 经验分享, 产品测评"
        )
        
        # 保存音频场景按钮
        if st.button("💾 保存音频场景", key="save_audio_scenes"):
            new_audio_scenes_list = [kw.strip() for kw in new_audio_scenes_str.split(",") if kw.strip()]
            try:
                updated_config = current_config.copy()
                updated_config["audio"]["scenes"] = new_audio_scenes_list
                keyword_manager.save_ai_recognition_config(updated_config)
                st.success("✅ 音频场景已保存!")
                st.rerun()
            except Exception as e:
                st.error(f"保存失败: {e}")
        
        # 情感配置提示 - 使用共用情绪
        st.write("**🎭 情感识别配置:**")
        st.info("💡 音频AI使用上方共用情绪配置，无需单独设置")
        
        # 音频场景细分配置
        st.markdown("---")
        st.write("**🎤 音频场景细分配置:**")
        
        # 喂养场景
        feeding_scenes_str = ", ".join(current_config["audio"].get("scenes_feeding", []))
        new_feeding_scenes_str = st.text_area(
            "🍼 喂养场景",
            value=feeding_scenes_str,
            key="deepseek_feeding_scenes",
            height=70,
            help="喂养相关场景，如：冲奶演示, 喂奶时刻, 辅食制作, 冲调"
        )
        
        # 互动场景
        interaction_scenes_str = ", ".join(current_config["audio"].get("scenes_interaction", []))
        new_interaction_scenes_str = st.text_area(
            "🤝 互动场景",
            value=interaction_scenes_str,
            key="deepseek_interaction_scenes",
            height=70,
            help="亲子互动场景，如：亲子游戏, 睡前准备, 户外活动"
        )
        
        # 分享场景
        sharing_scenes_str = ", ".join(current_config["audio"].get("scenes_sharing", []))
        new_sharing_scenes_str = st.text_area(
            "📢 分享场景",
            value=sharing_scenes_str,
            key="deepseek_sharing_scenes",
            height=70,
            help="经验分享场景，如：经验分享, 好物推荐, 产品测评, 答疑解惑"
        )
        
        # 生活场景
        lifestyle_scenes_str = ", ".join(current_config["audio"].get("scenes_lifestyle", []))
        new_lifestyle_scenes_str = st.text_area(
            "🏠 生活场景",
            value=lifestyle_scenes_str,
            key="deepseek_lifestyle_scenes",
            height=70,
            help="日常生活场景，如：日常vlog, 居家生活, 成长记录, 踩雷避坑"
        )
        
        # 保存音频场景细分按钮
        if st.button("💾 保存音频场景细分", key="save_audio_scene_details"):
            try:
                updated_config = current_config.copy()
                updated_config["audio"]["scenes_feeding"] = [s.strip() for s in new_feeding_scenes_str.split(",") if s.strip()]
                updated_config["audio"]["scenes_interaction"] = [s.strip() for s in new_interaction_scenes_str.split(",") if s.strip()]
                updated_config["audio"]["scenes_sharing"] = [s.strip() for s in new_sharing_scenes_str.split(",") if s.strip()]
                updated_config["audio"]["scenes_lifestyle"] = [s.strip() for s in new_lifestyle_scenes_str.split(",") if s.strip()]
                keyword_manager.save_ai_recognition_config(updated_config)
                st.success("✅ 音频场景细分已保存!")
                st.rerun()
            except Exception as e:
                st.error(f"保存失败: {e}")
    
    # 音频配置统计
    st.markdown("---")
    st.subheader("📊 音频AI配置统计")
    
    col_stat1, col_stat2, col_stat3, col_stat4, col_stat5 = st.columns(5)
    
    with col_stat1:
        audio_obj_count = len(current_config["audio"]["objects"])
        st.metric("基础识别对象", audio_obj_count)
    
    with col_stat2:
        audio_scenes_count = len(current_config["audio"]["scenes"])
        st.metric("识别场景", audio_scenes_count)
    
    with col_stat3:
        brand_mentions_count = len(current_config["audio"].get("brand_mentions", []))
        st.metric("品牌识别对象", brand_mentions_count)
    
    with col_stat4:
        product_features_count = len(current_config["audio"].get("product_features", []))
        st.metric("成分识别对象", product_features_count)
    
    with col_stat5:
        # 情感词汇已统一到共用配置，此处显示共用情绪数量
        shared_config = current_config.get("shared", {})
        ai_batch = shared_config.get("ai_batch", {})
        emotion_items = ai_batch.get("emotion", [])
        shared_emotions_count = len(emotion_items) if emotion_items else len(shared_config.get("emotions", []))
        st.metric("共用情感词汇", shared_emotions_count)


def _render_prompt_previews() -> None:
    """渲染AI模型Prompt预览界面"""
    st.markdown("#### 📝 AI模型Prompt预览")
    st.write("根据当前配置生成的AI模型指令预览（只读）")
    try:
        from utils.keyword_config import get_qwen_visual_prompt, get_deepseek_audio_prompt
        qwen_prompt = get_qwen_visual_prompt()
        deepseek_prompt = get_deepseek_audio_prompt()

        with st.expander("👁️ Qwen视觉分析Prompt", expanded=True):
            st.code(qwen_prompt, language="text")
            st.caption(f"Prompt长度: {len(qwen_prompt)} 字符")
        with st.expander("🧠 DeepSeek音频分析Prompt", expanded=False):
            st.code(deepseek_prompt, language="text")
            st.caption(f"Prompt长度: {len(deepseek_prompt)} 字符")

        # 配置效果分析等可保留原有逻辑
    except Exception as e:
        st.error(f"Prompt预览失败: {e}")
        st.info("请确保配置正确并已保存") 